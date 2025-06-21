"""
PDF處理模組
負責PDF文檔的解析、文本提取和初步清理
"""
import fitz  # PyMuPDF
import pdfplumber
from pathlib import Path
import re
import logging
from typing import List, Dict, Optional
from config import PDF_CONFIG, TEXT_CONFIG

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class PDFProcessor:
    """PDF文檔處理器"""
    
    def __init__(self):
        self.max_file_size = PDF_CONFIG["max_file_size_mb"] * 1024 * 1024
        self.supported_formats = PDF_CONFIG["supported_formats"]
    
    def validate_pdf(self, file_path: Path) -> bool:
        """驗證PDF文件"""
        if not file_path.exists():
            logger.error(f"文件不存在: {file_path}")
            return False
        
        if file_path.suffix.lower() not in self.supported_formats:
            logger.error(f"不支持的文件格式: {file_path.suffix}")
            return False
        
        if file_path.stat().st_size > self.max_file_size:
            logger.error(f"文件過大: {file_path.stat().st_size / 1024 / 1024:.2f}MB")
            return False
        
        return True
    
    def extract_text_pymupdf(self, file_path: Path) -> Dict[str, any]:
        """使用PyMuPDF提取文本"""
        try:
            doc = fitz.open(file_path)
            pages_text = []
            metadata = {
                "total_pages": len(doc),
                "title": doc.metadata.get("title", ""),
                "author": doc.metadata.get("author", ""),
                "subject": doc.metadata.get("subject", "")
            }
            
            for page_num in range(len(doc)):
                page = doc[page_num]
                text = page.get_text()
                
                # 清理文本
                text = self.clean_text(text)
                
                if text.strip():  # 只保存非空頁面
                    pages_text.append({
                        "page_number": page_num + 1,
                        "text": text,
                        "char_count": len(text)
                    })
            
            doc.close()
            
            return {
                "pages": pages_text,
                "metadata": metadata,
                "total_chars": sum(page["char_count"] for page in pages_text)
            }
            
        except Exception as e:
            logger.error(f"PyMuPDF提取失敗: {e}")
            return None
    
    def extract_text_pdfplumber(self, file_path: Path) -> Dict[str, any]:
        """使用pdfplumber提取文本（更好的表格處理）"""
        try:
            pages_text = []
            metadata = {}
            
            with pdfplumber.open(file_path) as pdf:
                metadata = {
                    "total_pages": len(pdf.pages),
                    "title": pdf.metadata.get("Title", ""),
                    "author": pdf.metadata.get("Author", ""),
                    "subject": pdf.metadata.get("Subject", "")
                }
                
                for page_num, page in enumerate(pdf.pages):
                    # 提取文本
                    text = page.extract_text() or ""
                    
                    # 提取表格
                    if PDF_CONFIG["extract_tables"]:
                        tables = page.extract_tables()
                        for table in tables:
                            table_text = self.format_table(table)
                            text += f"\n\n{table_text}\n\n"
                    
                    # 清理文本
                    text = self.clean_text(text)
                    
                    if text.strip():
                        pages_text.append({
                            "page_number": page_num + 1,
                            "text": text,
                            "char_count": len(text)
                        })
            
            return {
                "pages": pages_text,
                "metadata": metadata,
                "total_chars": sum(page["char_count"] for page in pages_text)
            }
            
        except Exception as e:
            logger.error(f"pdfplumber提取失敗: {e}")
            return None
    
    def format_table(self, table: List[List[str]]) -> str:
        """格式化表格為文本"""
        if not table:
            return ""
        
        formatted_rows = []
        for row in table:
            if row:  # 跳過空行
                clean_row = [cell.strip() if cell else "" for cell in row]
                formatted_rows.append(" | ".join(clean_row))
        
        return "\n".join(formatted_rows)
    
    def clean_text(self, text: str) -> str:
        """清理提取的文本"""
        if not text:
            return ""
        
        # 移除多餘的空白字符
        text = re.sub(r'\s+', ' ', text)
        
        # 移除頁眉頁腳（簡單規則）
        lines = text.split('\n')
        cleaned_lines = []
        
        for line in lines:
            line = line.strip()
            
            # 跳過可能的頁碼
            if re.match(r'^\d+$', line):
                continue
            
            # 跳過過短的行（可能是頁眉頁腳）
            if len(line) < 10:
                continue
            
            cleaned_lines.append(line)
        
        # 重新組合文本
        text = '\n'.join(cleaned_lines)
        
        # 修復常見的PDF提取問題
        text = re.sub(r'([a-z])([A-Z])', r'\1 \2', text)  # 添加缺失的空格
        text = re.sub(r'(\w)-\s*\n\s*(\w)', r'\1\2', text)  # 修復斷行的單詞
        
        return text.strip()
    
    def process_pdf(self, file_path: Path, method: str = "pdfplumber") -> Optional[Dict]:
        """處理PDF文件"""
        logger.info(f"開始處理PDF: {file_path}")
        
        if not self.validate_pdf(file_path):
            return None
        
        # 選擇提取方法
        if method == "pymupdf":
            result = self.extract_text_pymupdf(file_path)
        else:
            result = self.extract_text_pdfplumber(file_path)
        
        if result:
            logger.info(f"PDF處理完成: {result['metadata']['total_pages']}頁, "
                       f"{result['total_chars']}字符")
            
            # 添加文件信息
            result["file_info"] = {
                "file_name": file_path.name,
                "file_path": str(file_path),
                "file_size": file_path.stat().st_size,
                "extraction_method": method
            }
        
        return result

class TextSummarizer:
    """文本精簡器（可選：使用本地LLM進行文本精簡）"""
    
    def __init__(self):
        self.model_name = None
        self.model = None
        self.tokenizer = None
    
    def load_model(self):
        """加載文本精簡模型"""
        try:
            from transformers import AutoTokenizer, AutoModelForSeq2SeqLM
            
            logger.info(f"加載文本精簡模型: {self.model_name}")
            self.tokenizer = AutoTokenizer.from_pretrained(self.model_name)
            self.model = AutoModelForSeq2SeqLM.from_pretrained(self.model_name)
            
        except Exception as e:
            logger.error(f"模型加載失敗: {e}")
            self.model = None
            self.tokenizer = None
    
    def summarize_text(self, text: str, max_length: int = 512) -> str:
        """精簡文本"""
        if not self.model or not text.strip():
            return text
        
        try:
            # 如果文本已經很短，直接返回
            if len(text) < max_length:
                return text
            
            # 使用模型進行精簡
            inputs = self.tokenizer.encode(
                f"summarize: {text}",
                return_tensors="pt",
                max_length=1024,
                truncation=True
            )
            
            outputs = self.model.generate(
                inputs,
                max_length=max_length,
                min_length=50,
                length_penalty=2.0,
                num_beams=4,
                early_stopping=True
            )
            
            summary = self.tokenizer.decode(outputs[0], skip_special_tokens=True)
            return summary
            
        except Exception as e:
            logger.error(f"文本精簡失敗: {e}")
            return text
    
    def rule_based_summarize(self, text: str, ratio: float = 0.3) -> str:
        """基於規則的文本精簡"""
        sentences = re.split(r'[.!?。！？]', text)
        sentences = [s.strip() for s in sentences if s.strip()]
        
        if len(sentences) <= 3:
            return text
        
        # 保留前面和重要的句子
        keep_count = max(3, int(len(sentences) * ratio))
        
        # 簡單的重要性評分（基於長度和關鍵詞）
        scored_sentences = []
        for i, sentence in enumerate(sentences):
            score = len(sentence)  # 基礎分數
            
            # 位置權重（開頭和結尾的句子更重要）
            if i < 3:
                score *= 1.5
            elif i >= len(sentences) - 3:
                score *= 1.2
            
            scored_sentences.append((score, sentence))
        
        # 選擇最重要的句子
        scored_sentences.sort(reverse=True)
        selected = scored_sentences[:keep_count]
        
        # 按原順序重新排列
        result_sentences = []
        for _, sentence in selected:
            if sentence in sentences:
                result_sentences.append(sentence)
        
        return '。'.join(result_sentences) + '。'

# 使用示例
if __name__ == "__main__":
    processor = PDFProcessor()
    
    # 測試PDF處理
    pdf_path = Path("test.pdf")  # 替換為實際PDF路徑
    
    if pdf_path.exists():
        result = processor.process_pdf(pdf_path)
        if result:
            print(f"處理完成: {result['metadata']['total_pages']}頁")
            print(f"總字符數: {result['total_chars']}")
            
            # 顯示前100個字符
            if result['pages']:
                print(f"前100字符: {result['pages'][0]['text'][:100]}...")
    else:
        print("請提供有效的PDF文件路徑進行測試") 