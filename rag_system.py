import os
import logging
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path
import time
import traceback
import signal

from config import MODELS_CONFIG, TEXT_CONFIG, VECTOR_DB_CONFIG, RETRIEVAL_CONFIG, DATA_DIR, VECTOR_DB_DIR
from pdf_processor import PDFProcessor, TextSummarizer
from text_chunker import TextChunker, TextChunk
from vector_store import VectorStoreManager
from llm_manager import LLMManager

# 設置日誌
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('rag_system.log'),
        logging.StreamHandler()
    ]
)

class RAGSystem:
    """本地化RAG系統主類"""
    
    def __init__(self):
        """初始化RAG系統"""
        # 創建必要的目錄
        self._create_directories()
        
        # 初始化各個組件
        self.pdf_processor = PDFProcessor()
        self.text_summarizer = TextSummarizer()
        self.text_chunker = TextChunker()
        self.vector_store = VectorStoreManager()
        self.llm_manager = LLMManager()
        
        # 系統狀態
        self.processed_files: Dict[str, Dict[str, Any]] = {}
        
        logging.info("RAG System initialized successfully")
    
    def _create_directories(self):
        """創建必要的目錄"""
        directories = [
            DATA_DIR,
            VECTOR_DB_DIR,
            DATA_DIR / "processed",
            DATA_DIR / "summaries"
        ]
        
        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)
    
    def add_document(self, pdf_path: str, summarize: bool = True) -> Dict[str, Any]:
        """添加PDF文檔到系統"""
        start_time = time.time()
        
        try:
            # 檢查文件是否存在
            if not os.path.exists(pdf_path):
                raise FileNotFoundError(f"PDF file not found: {pdf_path}")
            
            filename = os.path.basename(pdf_path)
            logging.info(f"Processing document: {filename}")
            
            # 1. 提取PDF文本
            pdf_result = self.pdf_processor.process_pdf(Path(pdf_path))
            if not pdf_result or not pdf_result.get('pages'):
                raise ValueError("No text extracted from PDF")
            
            # 合併所有頁面的文本
            extracted_text = "\n\n".join([page['text'] for page in pdf_result['pages']])
            logging.info(f"Extracted {len(extracted_text)} characters from PDF")
            
            # 保存原始提取的文本到 processed 目錄
            processed_dir = DATA_DIR / "processed"
            processed_dir.mkdir(exist_ok=True)
            processed_file_path = processed_dir / f"{filename}_raw.txt"
            
            with open(processed_file_path, 'w', encoding='utf-8') as f:
                f.write(f"=== PDF 原始提取文本 ===\n")
                f.write(f"文件名: {filename}\n")
                f.write(f"頁數: {len(pdf_result['pages'])}\n")
                f.write(f"字符數: {len(extracted_text)}\n")
                f.write(f"提取時間: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write("=" * 50 + "\n\n")
                f.write(extracted_text)
            
            logging.info(f"Raw extracted text saved to: {processed_file_path}")
            
            # 2. 新流程：先切分再用 LLM 處理
            processed_text = extracted_text
            if summarize:
                logging.info("New flow: Chunking first, then LLM processing each chunk...")
                
                # 2.1 先進行預切分（為 LLM 處理準備）
                # 計算適合 LLM 處理的塊大小（考慮輸入+輸出的 token 限制）
                max_input_chars = 6000  # 保守估計，確保 LLM 能完整處理
                
                pre_chunks = self._create_llm_processing_chunks(extracted_text, max_input_chars)
                logging.info(f"Created {len(pre_chunks)} pre-chunks for LLM processing")
                
                # 2.2 用 LLM 處理每個預切分塊
                processed_chunks = []
                for i, chunk in enumerate(pre_chunks):
                    logging.info(f"Processing chunk {i+1}/{len(pre_chunks)} ({len(chunk)} chars)")
                    
                    processed_chunk = self.llm_manager.summarize_text(chunk)
                    
                    if processed_chunk and len(processed_chunk.strip()) >= 20:
                        processed_chunks.append(processed_chunk)
                        logging.info(f"Chunk {i+1} processed: {len(chunk)} -> {len(processed_chunk)} chars")
                    else:
                        logging.warning(f"Chunk {i+1} processing failed, using original")
                        processed_chunks.append(chunk)
                
                # 2.3 合併處理後的塊
                processed_text = "\n\n".join(processed_chunks)
                logging.info(f"All chunks processed: {len(extracted_text)} -> {len(processed_text)} characters")
                
                # 保存處理後的文本
                summary_path = DATA_DIR / "summaries" / f"{filename}_summary.txt"
                with open(summary_path, 'w', encoding='utf-8') as f:
                    f.write(f"=== LLM 處理後文本 ===\n")
                    f.write(f"原始長度: {len(extracted_text)} 字符\n")
                    f.write(f"處理後長度: {len(processed_text)} 字符\n")
                    f.write(f"壓縮比: {len(processed_text)/len(extracted_text)*100:.1f}%\n")
                    f.write(f"處理塊數: {len(pre_chunks)}\n")
                    f.write("=" * 50 + "\n\n")
                    f.write(processed_text)
            else:
                logging.info("Skipping LLM text processing as summarize=False")
            
            # 3. 最終切分（用於 embedding）
            logging.info("Final chunking for embedding...")
            chunks = self.text_chunker.chunk_text(
                processed_text, 
                source_file=filename
            )
            
            if not chunks:
                raise ValueError("No chunks created from text")
            
            logging.info(f"Created {len(chunks)} chunks")
            
            # 4. 添加到向量存儲（分批處理）
            logging.info(f"Adding {len(chunks)} chunks to vector store...")
            try:
                # 分批處理，避免一次性處理太多數據
                batch_size = 5  # 每批處理5個塊
                total_batches = (len(chunks) + batch_size - 1) // batch_size
                
                for i in range(0, len(chunks), batch_size):
                    batch_chunks = chunks[i:i + batch_size]
                    batch_num = i // batch_size + 1
                    
                    logging.info(f"Processing batch {batch_num}/{total_batches} ({len(batch_chunks)} chunks)")
                    
                    # 記錄開始時間
                    batch_start_time = time.time()
                    
                    try:
                        self.vector_store.add_chunks(batch_chunks)
                        batch_time = time.time() - batch_start_time
                        logging.info(f"✓ Batch {batch_num} completed in {batch_time:.2f}s")
                    except Exception as e:
                        batch_time = time.time() - batch_start_time
                        logging.error(f"✗ Batch {batch_num} failed after {batch_time:.2f}s: {e}")
                        raise
                
                logging.info("✓ All chunks added to vector store successfully")
                
            except Exception as e:
                logging.error(f"Failed to add chunks to vector store: {e}")
                raise Exception(f"Vector store operation failed: {e}")
            
            # 5. 記錄處理信息
            processing_time = time.time() - start_time
            chunk_stats = self.text_chunker.get_chunk_statistics(chunks)
            
            file_info = {
                "filename": filename,
                "original_path": pdf_path,
                "processed_at": time.strftime("%Y-%m-%d %H:%M:%S"),
                "processing_time": processing_time,
                "page_count": len(pdf_result.get('pages', [])),
                "character_count": len(extracted_text),
                "original_text_length": len(extracted_text),
                "processed_text_length": len(processed_text),
                "summarized": summarize and len(processed_text) < len(extracted_text),
                "chunk_count": len(chunks),
                "chunk_statistics": chunk_stats,
                "storage_status": "permanent"
            }
            
            self.processed_files[filename] = file_info
            
            logging.info(f"Document processed successfully in {processing_time:.2f} seconds")
            
            return {
                "success": True,
                "message": f"Document {filename} processed successfully",
                "file_info": file_info
            }
            
        except Exception as e:
            logging.error(f"Error processing document {pdf_path}: {e}")
            return {
                "success": False,
                "message": f"Error processing document: {str(e)}",
                "error": str(e)
            }
    
    def query(self, question: str, top_k: Optional[int] = None, use_rag: bool = True) -> Dict[str, Any]:
        """查詢系統"""
        start_time = time.time()
        
        try:
            if not question.strip():
                raise ValueError("Question cannot be empty")
            
            logging.info(f"Processing query: {question}, use_rag: {use_rag}")
            
            # 如果不使用RAG，直接用LLM回答
            if not use_rag:
                logging.info("Direct LLM mode - skipping RAG retrieval")
                answer = self.llm_manager.answer_question_direct(question)
                
                query_time = time.time() - start_time
                logging.info(f"Direct query processed in {query_time:.2f} seconds")
                
                return {
                    "success": True,
                    "answer": answer,
                    "sources": [],
                    "query_time": query_time,
                    "context_length": 0,
                    "chunks_used": 0,
                    "mode": "direct"
                }
            
            # 1. 向量搜索
            search_results = self.vector_store.search(question, top_k)
            
            if not search_results:
                return {
                    "success": True,
                    "answer": "抱歉，我在文檔中找不到相關信息來回答您的問題。",
                    "sources": [],
                    "query_time": time.time() - start_time,
                    "mode": "rag"
                }
            
            # 2. 準備上下文
            context_chunks = []
            sources = []
            
            for chunk, similarity in search_results:
                context_chunks.append(chunk.content)
                sources.append({
                    "source_file": chunk.metadata.get("source_file", "unknown"),
                    "chunk_index": chunk.metadata.get("chunk_index", 0),
                    "similarity": similarity,
                    "preview": chunk.content[:100] + "..." if len(chunk.content) > 100 else chunk.content
                })
            
            context = "\n\n".join(context_chunks)
            
            # 3. 生成回答
            logging.info("Generating answer...")
            answer = self.llm_manager.answer_question(question, context)
            
            if not answer:
                answer = "抱歉，我無法基於找到的信息生成回答。請嘗試重新表述您的問題。"
            
            query_time = time.time() - start_time
            
            logging.info(f"Query processed in {query_time:.2f} seconds")
            
            return {
                "success": True,
                "answer": answer,
                "sources": sources,
                "query_time": query_time,
                "context_length": len(context),
                "chunks_used": len(search_results),
                "mode": "rag"
            }
            
        except Exception as e:
            logging.error(f"Error processing query: {e}")
            return {
                "success": False,
                "answer": f"處理查詢時發生錯誤: {str(e)}",
                "error": str(e),
                "query_time": time.time() - start_time
            }
    
    def remove_document(self, filename: str, force: bool = False) -> Dict[str, Any]:
        """從系統中完全移除文檔（包括物理文件）
        
        Args:
            filename: 要刪除的文件名
            force: 是否強制刪除（即使不在processed_files中）
        """
        try:
            logging.info(f"開始刪除文檔: {filename}, 強制模式: {force}")
            
            # 檢查文件是否在記錄中
            file_exists_in_records = filename in self.processed_files
            
            if not file_exists_in_records and not force:
                logging.warning(f"文檔 {filename} 不在系統記錄中，使用 force=True 強制刪除")
                return {
                    "success": False,
                    "message": f"Document {filename} not found in system records. Use force=True to delete anyway.",
                    "suggestion": "如果確定要刪除，請使用強制刪除模式"
                }
            
            file_info = self.processed_files.get(filename, {})
            removed_items = []
            errors = []
            
            # 1. 從向量存儲中刪除（無論是否在記錄中都嘗試）
            try:
                logging.info(f"正在從向量數據庫刪除: {filename}")
                self.vector_store.delete_by_source(filename)
                removed_items.append("向量數據")
                logging.info(f"✓ 成功從向量數據庫刪除: {filename}")
            except Exception as e:
                error_msg = f"刪除向量數據失敗: {str(e)}"
                logging.error(error_msg)
                errors.append(error_msg)
            
            # 2. 刪除原始PDF文件
            original_path = file_info.get('original_path')
            if not original_path:
                # 如果沒有記錄路徑，嘗試在data目錄中查找
                data_dir = Path("./data")
                potential_path = data_dir / filename
                if potential_path.exists():
                    original_path = str(potential_path)
            
            if original_path and os.path.exists(original_path):
                try:
                    logging.info(f"正在刪除原始文件: {original_path}")
                    os.remove(original_path)
                    removed_items.append("原始PDF文件")
                    logging.info(f"✓ 成功刪除原始文件: {original_path}")
                except Exception as e:
                    error_msg = f"刪除原始文件失敗 {original_path}: {str(e)}"
                    logging.error(error_msg)
                    errors.append(error_msg)
            else:
                logging.warning(f"原始文件不存在或路徑未知: {original_path}")
            
            # 3. 刪除processed目錄中的原始提取文件（_raw.txt）
            processed_path = DATA_DIR / "processed" / f"{filename}_raw.txt"
            if processed_path.exists():
                try:
                    logging.info(f"正在刪除processed文件: {processed_path}")
                    processed_path.unlink()
                    removed_items.append("processed文件")
                    logging.info(f"✓ 成功刪除processed文件: {processed_path}")
                except Exception as e:
                    error_msg = f"刪除processed文件失敗 {processed_path}: {str(e)}"
                    logging.error(error_msg)
                    errors.append(error_msg)
            
            # 4. 刪除摘要文件（如果存在）
            summary_path = DATA_DIR / "summaries" / f"{filename}_summary.txt"
            if summary_path.exists():
                try:
                    logging.info(f"正在刪除摘要文件: {summary_path}")
                    summary_path.unlink()
                    removed_items.append("摘要文件")
                    logging.info(f"✓ 成功刪除摘要文件: {summary_path}")
                except Exception as e:
                    error_msg = f"刪除摘要文件失敗 {summary_path}: {str(e)}"
                    logging.error(error_msg)
                    errors.append(error_msg)
            
            # 5. 從記錄中移除（如果存在）
            if file_exists_in_records:
                try:
                    del self.processed_files[filename]
                    removed_items.append("系統記錄")
                    logging.info(f"✓ 成功從系統記錄中移除: {filename}")
                except Exception as e:
                    error_msg = f"從系統記錄移除失敗: {str(e)}"
                    logging.error(error_msg)
                    errors.append(error_msg)
            
            # 6. 檢查是否還有殘留的向量數據
            try:
                remaining_chunks = self._get_document_chunks(filename)
                if remaining_chunks:
                    logging.warning(f"發現殘留的向量數據: {len(remaining_chunks)} chunks")
                    errors.append(f"仍有 {len(remaining_chunks)} 個向量塊未清理")
            except Exception as e:
                logging.warning(f"檢查殘留數據時出錯: {e}")
            
            # 構建結果
            success = len(removed_items) > 0
            if success:
                logging.info(f"文檔 {filename} 刪除完成. 已移除: {', '.join(removed_items)}")
                if errors:
                    logging.warning(f"刪除過程中出現部分錯誤: {'; '.join(errors)}")
            else:
                logging.error(f"文檔 {filename} 刪除失敗，沒有任何項目被移除")
            
            return {
                "success": success,
                "message": f"Document {filename} {'partially' if errors else 'successfully'} removed" if success else f"Failed to remove document {filename}",
                "removed_items": removed_items,
                "errors": errors,
                "details": {
                    "filename": filename,
                    "force_mode": force,
                    "was_in_records": file_exists_in_records,
                    "removed_components": removed_items,
                    "original_path": original_path,
                    "errors_encountered": errors
                }
            }
            
        except Exception as e:
            error_msg = f"刪除文檔 {filename} 時發生嚴重錯誤: {str(e)}"
            logging.error(error_msg)
            logging.error(traceback.format_exc())
            return {
                "success": False,
                "message": error_msg,
                "error": str(e),
                "details": {
                    "filename": filename,
                    "force_mode": force,
                    "exception": str(e)
                }
            }
    
    def cleanup_orphaned_data(self) -> Dict[str, Any]:
        """清理孤立的向量數據（定期維護功能）"""
        try:
            logging.info("開始清理孤立的向量數據...")
            
            # 獲取data目錄中實際存在的PDF文件
            data_dir = Path("./data")
            existing_files = set()
            if data_dir.exists():
                for pdf_file in data_dir.glob("*.pdf"):
                    existing_files.add(pdf_file.name)
            
            # 獲取向量數據庫中的所有源文件
            results = self.vector_store.store.collection.get(include=['metadatas'])
            
            if not results or not results.get('metadatas'):
                return {
                    "success": True,
                    "message": "向量數據庫為空，無需清理",
                    "orphaned_files": [],
                    "cleaned_count": 0
                }
            
            vector_files = set()
            for metadata in results['metadatas']:
                if 'source_file' in metadata:
                    vector_files.add(metadata['source_file'])
            
            # 找出孤立的文件
            orphaned_files = vector_files - existing_files
            
            logging.info(f"發現 {len(orphaned_files)} 個孤立文件")
            
            cleaned_files = []
            errors = []
            
            # 清理孤立的文件
            for orphaned_file in orphaned_files:
                try:
                    logging.info(f"清理孤立文件: {orphaned_file}")
                    result = self.remove_document(orphaned_file, force=True)
                    if result['success']:
                        cleaned_files.append(orphaned_file)
                        logging.info(f"✓ 已清理: {orphaned_file}")
                    else:
                        errors.append(f"{orphaned_file}: {result.get('message', '未知錯誤')}")
                        logging.error(f"✗ 清理失敗: {orphaned_file}")
                except Exception as e:
                    error_msg = f"{orphaned_file}: {str(e)}"
                    errors.append(error_msg)
                    logging.error(f"✗ 清理異常: {error_msg}")
            
            logging.info(f"孤立數據清理完成. 成功: {len(cleaned_files)}, 失敗: {len(errors)}")
            
            return {
                "success": True,
                "message": f"清理完成，處理了 {len(orphaned_files)} 個孤立文件",
                "orphaned_files": list(orphaned_files),
                "cleaned_files": cleaned_files,
                "cleaned_count": len(cleaned_files),
                "errors": errors,
                "details": {
                    "total_existing_files": len(existing_files),
                    "total_vector_files": len(vector_files),
                    "orphaned_count": len(orphaned_files),
                    "successfully_cleaned": len(cleaned_files),
                    "failed_count": len(errors)
                }
            }
            
        except Exception as e:
            error_msg = f"清理孤立數據時發生錯誤: {str(e)}"
            logging.error(error_msg)
            logging.error(traceback.format_exc())
            return {
                "success": False,
                "message": error_msg,
                "error": str(e)
            }
    
    def remove_all_documents(self) -> Dict[str, Any]:
        """刪除所有文檔（危險操作，僅供後端使用）"""
        try:
            logging.info("開始刪除所有文檔...")
            
            # 獲取所有文檔列表
            all_documents = self.list_documents()
            
            if not all_documents:
                return {
                    "success": True,
                    "message": "沒有文檔需要刪除",
                    "deleted_count": 0,
                    "failed_count": 0,
                    "deleted_files": [],
                    "failed_files": []
                }
            
            deleted_files = []
            failed_files = []
            
            # 逐個刪除文檔
            for doc in all_documents:
                filename = doc.get('filename')
                if not filename:
                    continue
                    
                try:
                    logging.info(f"正在刪除文檔: {filename}")
                    result = self.remove_document(filename, force=True)
                    
                    if result['success']:
                        deleted_files.append({
                            'filename': filename,
                            'removed_items': result.get('removed_items', [])
                        })
                        logging.info(f"✓ 成功刪除: {filename}")
                    else:
                        failed_files.append({
                            'filename': filename,
                            'error': result.get('message', '未知錯誤')
                        })
                        logging.error(f"✗ 刪除失敗: {filename}")
                        
                except Exception as e:
                    error_msg = f"刪除 {filename} 時發生異常: {str(e)}"
                    failed_files.append({
                        'filename': filename,
                        'error': error_msg
                    })
                    logging.error(error_msg)
            
            # 額外清理：嘗試清理向量數據庫中的所有數據
            try:
                logging.info("清理向量數據庫中的所有數據...")
                self.vector_store.store.collection.delete()
                logging.info("✓ 向量數據庫已清空")
            except Exception as e:
                logging.error(f"清理向量數據庫失敗: {str(e)}")
            
            # 清空processed_files記錄
            try:
                self.processed_files.clear()
                logging.info("✓ 系統記錄已清空")
            except Exception as e:
                logging.error(f"清空系統記錄失敗: {str(e)}")
            
            deleted_count = len(deleted_files)
            failed_count = len(failed_files)
            total_count = len(all_documents)
            
            logging.info(f"批量刪除完成. 總計: {total_count}, 成功: {deleted_count}, 失敗: {failed_count}")
            
            return {
                "success": True,
                "message": f"批量刪除完成. 總計: {total_count}, 成功: {deleted_count}, 失敗: {failed_count}",
                "total_count": total_count,
                "deleted_count": deleted_count,
                "failed_count": failed_count,
                "deleted_files": deleted_files,
                "failed_files": failed_files
            }
            
        except Exception as e:
            error_msg = f"批量刪除文檔時發生嚴重錯誤: {str(e)}"
            logging.error(error_msg)
            logging.error(traceback.format_exc())
            return {
                "success": False,
                "message": error_msg,
                "error": str(e)
            }
    
    def check_data_consistency(self) -> Dict[str, Any]:
        """檢查數據一致性"""
        try:
            logging.info("開始數據一致性檢查...")
            
            # 獲取各種數據源
            data_dir = Path("./data")
            existing_files = set()
            if data_dir.exists():
                for pdf_file in data_dir.glob("*.pdf"):
                    existing_files.add(pdf_file.name)
            
            recorded_files = set(self.processed_files.keys())
            
            # 獲取向量數據庫中的文件
            vector_files = set()
            try:
                results = self.vector_store.store.collection.get(include=['metadatas'])
                if results and results.get('metadatas'):
                    for metadata in results['metadatas']:
                        if 'source_file' in metadata:
                            vector_files.add(metadata['source_file'])
            except Exception as e:
                logging.error(f"檢查向量數據庫時出錯: {e}")
            
            # 分析不一致情況
            issues = []
            
            # 1. 文件存在但沒有記錄
            files_without_records = existing_files - recorded_files
            if files_without_records:
                issues.append({
                    "type": "missing_records",
                    "description": "文件存在但沒有處理記錄",
                    "files": list(files_without_records),
                    "count": len(files_without_records)
                })
            
            # 2. 有記錄但文件不存在
            records_without_files = recorded_files - existing_files
            if records_without_files:
                issues.append({
                    "type": "missing_files",
                    "description": "有處理記錄但文件不存在",
                    "files": list(records_without_files),
                    "count": len(records_without_files)
                })
            
            # 3. 向量數據孤立
            orphaned_vectors = vector_files - existing_files
            if orphaned_vectors:
                issues.append({
                    "type": "orphaned_vectors",
                    "description": "向量數據存在但文件不存在",
                    "files": list(orphaned_vectors),
                    "count": len(orphaned_vectors)
                })
            
            # 4. 文件存在但沒有向量數據
            files_without_vectors = existing_files - vector_files
            if files_without_vectors:
                issues.append({
                    "type": "missing_vectors",
                    "description": "文件存在但沒有向量數據",
                    "files": list(files_without_vectors),
                    "count": len(files_without_vectors)
                })
            
            is_consistent = len(issues) == 0
            
            logging.info(f"數據一致性檢查完成. 一致性: {is_consistent}, 發現問題: {len(issues)}")
            
            return {
                "consistent": is_consistent,
                "total_files": len(existing_files),
                "total_records": len(recorded_files),
                "total_vectors": len(vector_files),
                "issues": issues,
                "issue_count": len(issues),
                "details": {
                    "existing_files": sorted(list(existing_files)),
                    "recorded_files": sorted(list(recorded_files)),
                    "vector_files": sorted(list(vector_files))
                }
            }
            
        except Exception as e:
            error_msg = f"數據一致性檢查時發生錯誤: {str(e)}"
            logging.error(error_msg)
            logging.error(traceback.format_exc())
            return {
                "consistent": False,
                "error": str(e),
                "message": error_msg
            }
    
    def get_system_status(self) -> Dict[str, Any]:
        """獲取系統狀態"""
        try:
            vector_stats = self.vector_store.get_stats()
            llm_providers = self.llm_manager.get_available_providers()
            
            return {
                "system_ready": len(llm_providers) > 0,
                "processed_documents": len(self.processed_files),
                "vector_store_stats": vector_stats,
                "available_llm_providers": llm_providers,
                "current_llm_provider": self.llm_manager._get_current_provider_name(),
                "config": {
                    "chunk_size": TEXT_CONFIG["max_chunk_size"],
                    "chunk_overlap": TEXT_CONFIG["chunk_overlap"],
                    "top_k": RETRIEVAL_CONFIG["top_k"],
                    "similarity_threshold": RETRIEVAL_CONFIG["similarity_threshold"]
                }
            }
            
        except Exception as e:
            logging.error(f"Error getting system status: {e}")
            return {
                "error": str(e)
            }
    
    def get_document_list(self) -> List[Dict[str, Any]]:
        """獲取已處理文檔列表"""
        return list(self.processed_files.values())
    
    def list_documents(self) -> List[Dict[str, Any]]:
        """獲取已處理文檔列表（API兼容方法）"""
        # 從資料夾掃描現有文檔
        self._scan_existing_documents()
        return self.get_document_list()
    
    def _scan_existing_documents(self):
        """掃描data目錄中的現有文檔"""
        try:
            data_dir = Path("./data")
            if not data_dir.exists():
                return
            
            # 掃描PDF文件
            for pdf_file in data_dir.glob("*.pdf"):
                filename = pdf_file.name
                
                # 如果文檔還沒有記錄，創建基本記錄
                if filename not in self.processed_files:
                    # 檢查是否在向量數據庫中有對應的chunks
                    chunks_exist = self._check_document_in_vector_store(filename)
                    
                    if chunks_exist:
                        # 創建基本文檔記錄
                        file_stats = pdf_file.stat()
                        self.processed_files[filename] = {
                            "filename": filename,
                            "original_path": str(pdf_file),
                            "processed_at": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(file_stats.st_mtime)),
                            "processing_time": 0,
                            "page_count": 0,
                            "character_count": file_stats.st_size,  # 使用文件大小作為估算
                            "chunk_count": len(self._get_document_chunks(filename)),
                            "storage_status": "permanent"
                        }
                        logging.info(f"發現現有文檔: {filename}")
        except Exception as e:
            logging.error(f"掃描現有文檔失敗: {e}")
    
    def _check_document_in_vector_store(self, filename: str) -> bool:
        """檢查文檔是否在向量數據庫中"""
        try:
            # 嘗試搜索該文檔的chunks
            chunks = self._get_document_chunks(filename)
            return len(chunks) > 0
        except Exception:
            return False
    
    def _get_document_chunks(self, filename: str) -> List:
        """獲取文檔的所有chunks"""
        try:
            # 使用向量存儲的方法獲取特定文檔的chunks
            return self.vector_store.get_chunks_by_source(filename)
        except Exception:
            return []
    
    def search_documents(self, query: str, top_k: int = 10) -> List[Dict[str, Any]]:
        """搜索文檔片段（不生成回答）"""
        try:
            search_results = self.vector_store.search(query, top_k)
            
            results = []
            for chunk, similarity in search_results:
                results.append({
                    "content": chunk.content,
                    "source_file": chunk.metadata.get("source_file", "unknown"),
                    "chunk_index": chunk.metadata.get("chunk_index", 0),
                    "similarity": similarity,
                    "metadata": chunk.metadata
                })
            
            return results
            
        except Exception as e:
            logging.error(f"Error searching documents: {e}")
            return []
    
    def update_config(self, new_config: Dict[str, Any]) -> Dict[str, Any]:
        """更新系統配置"""
        try:
            # 更新配置
            for key, value in new_config.items():
                if hasattr(self.config, key):
                    setattr(self.config, key, value)
            
            # 重新初始化需要的組件
            if any(key.startswith('llm_') for key in new_config.keys()):
                self.llm_manager = LLMManager(self.config)
            
            if any(key in ['chunk_size', 'chunk_overlap', 'chunking_method'] for key in new_config.keys()):
                self.text_chunker = TextChunker(self.config)
            
            return {
                "success": True,
                "message": "Configuration updated successfully"
            }
            
        except Exception as e:
            logging.error(f"Error updating config: {e}")
            return {
                "success": False,
                "message": f"Error updating configuration: {str(e)}",
                "error": str(e)
            }
    
    def export_data(self, export_path: str) -> Dict[str, Any]:
        """導出系統數據"""
        try:
            import json
            
            export_data = {
                "processed_files": self.processed_files,
                "config": self.config.__dict__,
                "export_timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
            }
            
            with open(export_path, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, ensure_ascii=False, indent=2)
            
            return {
                "success": True,
                "message": f"Data exported to {export_path}"
            }
            
        except Exception as e:
            logging.error(f"Error exporting data: {e}")
            return {
                "success": False,
                "message": f"Error exporting data: {str(e)}",
                "error": str(e)
            }
    
    def _create_llm_processing_chunks(self, text: str, max_chars: int) -> List[str]:
        """
        為 LLM 處理創建合適大小的文本塊
        
        Args:
            text: 要切分的文本
            max_chars: 每塊的最大字符數
            
        Returns:
            文本塊列表
        """
        if len(text) <= max_chars:
            return [text]
        
        chunks = []
        
        # 按段落分割
        paragraphs = text.split('\n\n')
        current_chunk = ""
        
        for paragraph in paragraphs:
            paragraph = paragraph.strip()
            if not paragraph:
                continue
            
            # 如果單個段落就超過限制，需要進一步切分
            if len(paragraph) > max_chars:
                # 先保存當前塊（如果有內容）
                if current_chunk:
                    chunks.append(current_chunk.strip())
                    current_chunk = ""
                
                # 按句子切分長段落
                sentences = self._split_paragraph_by_sentences(paragraph)
                temp_chunk = ""
                
                for sentence in sentences:
                    if len(temp_chunk) + len(sentence) + 2 <= max_chars:
                        temp_chunk += sentence + " "
                    else:
                        if temp_chunk:
                            chunks.append(temp_chunk.strip())
                        temp_chunk = sentence + " "
                
                if temp_chunk:
                    current_chunk = temp_chunk
            else:
                # 檢查加入這個段落是否會超過限制
                if len(current_chunk) + len(paragraph) + 2 <= max_chars:
                    current_chunk += paragraph + "\n\n"
                else:
                    # 保存當前塊，開始新塊
                    if current_chunk:
                        chunks.append(current_chunk.strip())
                    current_chunk = paragraph + "\n\n"
        
        # 保存最後一塊
        if current_chunk:
            chunks.append(current_chunk.strip())
        
        # 過濾掉太短的塊
        chunks = [chunk for chunk in chunks if len(chunk.strip()) >= 50]
        
        return chunks
    
    def _split_paragraph_by_sentences(self, paragraph: str) -> List[str]:
        """
        按句子切分段落
        
        Args:
            paragraph: 要切分的段落
            
        Returns:
            句子列表
        """
        import re
        
        # 中英文句子分隔符
        sentence_endings = r'[.!?。！？]+'
        sentences = re.split(sentence_endings, paragraph)
        
        # 重新添加標點符號
        result = []
        parts = re.findall(sentence_endings, paragraph)
        
        for i, sentence in enumerate(sentences):
            sentence = sentence.strip()
            if sentence:
                if i < len(parts):
                    sentence += parts[i]
                result.append(sentence)
        
        return result 