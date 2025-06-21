import os
import json
import pickle
import numpy as np
from typing import List, Dict, Any, Optional, Tuple
from abc import ABC, abstractmethod
import logging
from pathlib import Path

# 向量數據庫相關導入
try:
    import chromadb
    from chromadb.config import Settings
    CHROMA_AVAILABLE = True
except ImportError:
    CHROMA_AVAILABLE = False
    logging.warning("ChromaDB not available. Install with: pip install chromadb")

try:
    import faiss
    FAISS_AVAILABLE = True
except ImportError:
    FAISS_AVAILABLE = False
    logging.warning("FAISS not available. Install with: pip install faiss-cpu")

try:
    from sentence_transformers import SentenceTransformer
    SENTENCE_TRANSFORMERS_AVAILABLE = True
except ImportError:
    SENTENCE_TRANSFORMERS_AVAILABLE = False

try:
    from ollama import Client
    OLLAMA_AVAILABLE = True
except ImportError:
    OLLAMA_AVAILABLE = False

from text_chunker import TextChunk
from config import VECTOR_DB_CONFIG, RETRIEVAL_CONFIG, VECTOR_DB_DIR, MODELS_CONFIG

class EmbeddingProvider:
    """嵌入向量提供者基類"""
    
    def __init__(self):
        self.embedding_config = MODELS_CONFIG["embedding"]
        
    def get_embeddings(self, texts):
        """獲取文本的嵌入向量"""
        if self.embedding_config["provider"] == "ollama":
            return self._get_ollama_embeddings(texts)
        elif self.embedding_config["provider"] == "sentence_transformers":
            return self._get_sentence_transformers_embeddings(texts)
        else:
            raise ValueError(f"Unsupported embedding provider: {self.embedding_config['provider']}")
    
    def _get_ollama_embeddings(self, texts):
        """使用 Ollama 獲取嵌入向量"""
        if not OLLAMA_AVAILABLE:
            raise ImportError("Ollama not available. Please install: pip install ollama")
        
        client = Client(host=self.embedding_config["base_url"])
        embeddings = []
        
        for text in texts:
            try:
                res = client.embeddings(
                    model=self.embedding_config["model_name"],
                    prompt=text
                )
                embeddings.append(res['embedding'])
            except Exception as e:
                logging.error(f"Error getting embedding for text: {e}")
                # 返回零向量作為備用
                embeddings.append([0.0] * self.embedding_config["dimension"])
        
        return embeddings
    
    def _get_sentence_transformers_embeddings(self, texts):
        """使用 sentence-transformers 獲取嵌入向量"""
        if not SENTENCE_TRANSFORMERS_AVAILABLE:
            raise ImportError("sentence-transformers not available")
        
        if not hasattr(self, '_st_model'):
            self._st_model = SentenceTransformer(self.embedding_config["model_name"])
        
        return self._st_model.encode(texts).tolist()

class VectorStore(ABC):
    """向量存儲抽象基類"""
    
    @abstractmethod
    def add_chunks(self, chunks: List[TextChunk]) -> None:
        """添加文本塊到向量存儲"""
        pass
    
    @abstractmethod
    def search(self, query: str, top_k: int = 5) -> List[Tuple[TextChunk, float]]:
        """搜索相似文本塊"""
        pass
    
    @abstractmethod
    def delete_by_source(self, source_file: str) -> None:
        """根據源文件刪除文本塊"""
        pass
    
    @abstractmethod
    def get_stats(self) -> Dict[str, Any]:
        """獲取存儲統計信息"""
        pass

class ChromaVectorStore(VectorStore):
    """ChromaDB向量存儲實現"""
    
    def __init__(self):
        if not CHROMA_AVAILABLE:
            raise ImportError("ChromaDB is not available. Please install it with: pip install chromadb")
        
        self.collection_name = VECTOR_DB_CONFIG["collection_name"]
        self.embedding_provider = EmbeddingProvider()
        
        # 初始化ChromaDB
        self.client = chromadb.PersistentClient(
            path=str(VECTOR_DB_DIR),
            settings=Settings(
                anonymized_telemetry=False,
                allow_reset=True
            )
        )
        
        # 創建或獲取集合
        self.collection = self.client.get_or_create_collection(
            name=self.collection_name,
            metadata={"description": "RAG document chunks"}
        )
        
        logging.info(f"ChromaDB initialized at {VECTOR_DB_DIR}")
    
    def add_chunks(self, chunks: List[TextChunk]) -> None:
        """添加文本塊到ChromaDB"""
        if not chunks:
            return
        
        # 準備數據
        documents = [chunk.content for chunk in chunks]
        metadatas = [chunk.metadata for chunk in chunks]
        ids = [chunk.chunk_id for chunk in chunks]
        
        # 生成嵌入向量
        embeddings = self.embedding_provider.get_embeddings(documents)
        
        # 添加到集合
        self.collection.add(
            documents=documents,
            metadatas=metadatas,
            ids=ids,
            embeddings=embeddings
        )
        
        logging.info(f"Added {len(chunks)} chunks to ChromaDB")
    
    def search(self, query: str, top_k: int = 5) -> List[Tuple[TextChunk, float]]:
        """搜索相似文本塊"""
        # 生成查詢嵌入
        query_embedding = self.embedding_provider.get_embeddings([query])
        
        # 執行搜索
        results = self.collection.query(
            query_embeddings=query_embedding,
            n_results=top_k,
            include=['documents', 'metadatas', 'distances']
        )
        
        # 轉換結果
        search_results = []
        if results['documents'] and results['documents'][0]:
            for i in range(len(results['documents'][0])):
                chunk = TextChunk(
                    content=results['documents'][0][i],
                    metadata=results['metadatas'][0][i],
                    token_count=len(results['documents'][0][i].split()),  # 簡單估算
                    chunk_id=results['ids'][0][i] if 'ids' in results else f"result_{i}"
                )
                # ChromaDB返回的是平方歐氏距離，需要正確轉換為相似度
                distance = results['distances'][0][i]
                # 對於負距離值，直接使用絕對值的倒數作為相似度
                if distance < 0:
                    similarity = 1.0 / (1.0 + abs(distance))
                else:
                    similarity = 1.0 / (1.0 + distance)
                search_results.append((chunk, similarity))
        
        return search_results
    
    def delete_by_source(self, source_file: str) -> None:
        """根據源文件刪除文本塊"""
        try:
            # 查詢該源文件的所有文檔
            results = self.collection.get(
                where={"source_file": source_file}
            )
            
            if results and results.get('ids'):
                self.collection.delete(ids=results['ids'])
                logging.info(f"Deleted {len(results['ids'])} chunks from source: {source_file}")
            else:
                logging.warning(f"No chunks found for source: {source_file}")
        
        except Exception as e:
            logging.error(f"Error deleting chunks by source {source_file}: {e}")
            # 嘗試使用where條件直接刪除
            try:
                self.collection.delete(where={"source_file": source_file})
                logging.info(f"Deleted chunks from source using where condition: {source_file}")
            except Exception as e2:
                logging.error(f"Failed to delete using where condition: {e2}")
                raise e

    def get_stats(self) -> Dict[str, Any]:
        """獲取存儲統計信息"""
        count = self.collection.count()
        return {
            "total_chunks": count,
            "collection_name": self.collection.name,
            "embedding_provider": self.embedding_provider.embedding_config["provider"],
            "embedding_model": self.embedding_provider.embedding_config["model_name"]
        }
    
    def get_chunks_by_source(self, source_file: str) -> List[Dict]:
        """根據源文件獲取所有chunks"""
        try:
            results = self.collection.get(
                where={"source_file": source_file},
                include=["documents", "metadatas"]
            )
            
            chunks = []
            if results and results.get('documents'):
                for i, doc in enumerate(results['documents']):
                    metadata = results['metadatas'][i] if results.get('metadatas') else {}
                    chunks.append({
                        'content': doc,
                        'metadata': metadata
                    })
            
            return chunks
        except Exception as e:
            logging.error(f"Error getting chunks by source {source_file}: {e}")
            return []

class FAISSVectorStore(VectorStore):
    """FAISS向量存儲實現"""
    
    def __init__(self):
        if not FAISS_AVAILABLE:
            raise ImportError("FAISS is not available. Please install it with: pip install faiss-cpu")
        
        self.embedding_provider = EmbeddingProvider()
        
        # 初始化FAISS索引
        self.dimension = self.embedding_provider.embedding_config["dimension"]
        self.index = faiss.IndexFlatIP(self.dimension)  # 內積索引
        
        # 存儲文檔和元數據
        self.chunks: List[TextChunk] = []
        self.chunk_id_to_index: Dict[str, int] = {}
        
        # 加載已存在的索引
        self._load_index()
        
        logging.info(f"FAISS initialized with dimension {self.dimension}")
    
    def add_chunks(self, chunks: List[TextChunk]) -> None:
        """添加文本塊到FAISS"""
        if not chunks:
            return
        
        # 生成嵌入向量
        documents = [chunk.content for chunk in chunks]
        embeddings = np.array(self.embedding_provider.get_embeddings(documents))
        
        # 正規化向量（用於內積相似度）
        faiss.normalize_L2(embeddings)
        
        # 添加到索引
        start_index = len(self.chunks)
        self.index.add(embeddings)
        
        # 更新內部存儲
        for i, chunk in enumerate(chunks):
            self.chunks.append(chunk)
            self.chunk_id_to_index[chunk.chunk_id] = start_index + i
        
        # 保存索引
        self._save_index()
        
        logging.info(f"Added {len(chunks)} chunks to FAISS")
    
    def search(self, query: str, top_k: int = 5) -> List[Tuple[TextChunk, float]]:
        """搜索相似文本塊"""
        if self.index.ntotal == 0:
            return []
        
        # 生成查詢嵌入
        query_embedding = np.array(self.embedding_provider.get_embeddings([query]))
        faiss.normalize_L2(query_embedding)
        
        # 執行搜索
        similarities, indices = self.index.search(query_embedding, min(top_k, self.index.ntotal))
        
        # 轉換結果
        search_results = []
        for i in range(len(indices[0])):
            if indices[0][i] != -1:  # FAISS用-1表示無效結果
                chunk = self.chunks[indices[0][i]]
                similarity = float(similarities[0][i])
                search_results.append((chunk, similarity))
        
        return search_results
    
    def delete_by_source(self, source_file: str) -> None:
        """根據源文件刪除文本塊"""
        # FAISS不支持直接刪除，需要重建索引
        indices_to_remove = []
        for i, chunk in enumerate(self.chunks):
            if chunk.metadata.get("source_file") == source_file:
                indices_to_remove.append(i)
        
        if not indices_to_remove:
            return
        
        # 創建新的數據結構
        new_chunks = []
        new_chunk_id_to_index = {}
        
        for i, chunk in enumerate(self.chunks):
            if i not in indices_to_remove:
                new_index = len(new_chunks)
                new_chunks.append(chunk)
                new_chunk_id_to_index[chunk.chunk_id] = new_index
        
        # 重建索引
        if new_chunks:
            documents = [chunk.content for chunk in new_chunks]
            embeddings = np.array(self.embedding_provider.get_embeddings(documents))
            faiss.normalize_L2(embeddings)
            
            self.index = faiss.IndexFlatIP(self.dimension)
            self.index.add(embeddings)
        else:
            self.index = faiss.IndexFlatIP(self.dimension)
        
        # 更新內部存儲
        self.chunks = new_chunks
        self.chunk_id_to_index = new_chunk_id_to_index
        
        # 保存索引
        self._save_index()
        
        logging.info(f"Deleted {len(indices_to_remove)} chunks from source: {source_file}")
    
    def get_stats(self) -> Dict[str, Any]:
        """獲取存儲統計信息"""
        return {
            "total_chunks": len(self.chunks),
            "index_size": self.index.ntotal,
            "dimension": self.dimension,
            "embedding_model": self.embedding_model_name
        }
    
    def _save_index(self) -> None:
        """保存FAISS索引和元數據"""
        VECTOR_DB_DIR.mkdir(parents=True, exist_ok=True)
        
        # 保存FAISS索引
        index_path = VECTOR_DB_DIR / "faiss.index"
        faiss.write_index(self.index, str(index_path))
        
        # 保存元數據
        metadata_path = VECTOR_DB_DIR / "metadata.pkl"
        with open(metadata_path, 'wb') as f:
            pickle.dump({
                'chunks': self.chunks,
                'chunk_id_to_index': self.chunk_id_to_index
            }, f)
    
    def _load_index(self) -> None:
        """加載FAISS索引和元數據"""
        index_path = VECTOR_DB_DIR / "faiss.index"
        metadata_path = VECTOR_DB_DIR / "metadata.pkl"
        
        if index_path.exists() and metadata_path.exists():
            try:
                # 加載FAISS索引
                self.index = faiss.read_index(str(index_path))
                
                # 加載元數據
                with open(metadata_path, 'rb') as f:
                    metadata = pickle.load(f)
                    self.chunks = metadata['chunks']
                    self.chunk_id_to_index = metadata['chunk_id_to_index']
                
                logging.info(f"Loaded existing FAISS index with {len(self.chunks)} chunks")
            except Exception as e:
                logging.warning(f"Failed to load existing index: {e}")
                # 重新初始化
                self.index = faiss.IndexFlatIP(self.dimension)
                self.chunks = []
                self.chunk_id_to_index = {}

class VectorStoreManager:
    """向量存儲管理器"""
    
    def __init__(self):
        self.vector_db_type = VECTOR_DB_CONFIG["type"]
        self.top_k = RETRIEVAL_CONFIG["top_k"]
        self.similarity_threshold = RETRIEVAL_CONFIG["similarity_threshold"]
        self.enable_reranking = RETRIEVAL_CONFIG["enable_reranking"]
        self.store = self._create_vector_store()
    
    def _create_vector_store(self) -> VectorStore:
        """創建向量存儲實例"""
        if self.vector_db_type.lower() == "chroma":
            if not CHROMA_AVAILABLE:
                raise ImportError("ChromaDB not available")
            return ChromaVectorStore()
        else:
            raise ValueError(f"Unsupported vector database type: {self.vector_db_type}")
    
    def add_chunks(self, chunks: List[TextChunk]) -> None:
        """添加文本塊"""
        self.store.add_chunks(chunks)
    
    def search(self, query: str, top_k: Optional[int] = None) -> List[Tuple[TextChunk, float]]:
        """搜索相似文本塊"""
        if top_k is None:
            top_k = self.top_k
        
        results = self.store.search(query, top_k)
        
        # 應用相似度閾值過濾
        filtered_results = [
            (chunk, score) for chunk, score in results 
            if score >= self.similarity_threshold
        ]
        
        return filtered_results
    
    def delete_by_source(self, source_file: str) -> None:
        """根據源文件刪除文本塊"""
        self.store.delete_by_source(source_file)
    
    def get_stats(self) -> Dict[str, Any]:
        """獲取存儲統計信息"""
        return self.store.get_stats()
    
    def get_chunks_by_source(self, source_file: str) -> List[Dict]:
        """根據源文件獲取所有chunks"""
        if hasattr(self.store, 'get_chunks_by_source'):
            return self.store.get_chunks_by_source(source_file)
        return []
    
    def rerank_results(self, query: str, results: List[Tuple[TextChunk, float]]) -> List[Tuple[TextChunk, float]]:
        """重新排序搜索結果（可選功能）"""
        if not self.enable_reranking or not results:
            return results
        
        # 簡單的重排序策略：基於查詢詞匹配度
        def calculate_keyword_score(chunk: TextChunk, query: str) -> float:
            query_words = set(query.lower().split())
            chunk_words = set(chunk.content.lower().split())
            
            if not query_words:
                return 0.0
            
            intersection = query_words.intersection(chunk_words)
            return len(intersection) / len(query_words)
        
        # 計算組合分數
        reranked_results = []
        for chunk, semantic_score in results:
            keyword_score = calculate_keyword_score(chunk, query)
            combined_score = 0.7 * semantic_score + 0.3 * keyword_score
            reranked_results.append((chunk, combined_score))
        
        # 按組合分數排序
        reranked_results.sort(key=lambda x: x[1], reverse=True)
        
        return reranked_results 