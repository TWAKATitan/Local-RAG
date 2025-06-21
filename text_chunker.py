import re
import nltk
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
import tiktoken
from config import TEXT_CONFIG

# 下載必要的NLTK數據
try:
    nltk.data.find('tokenizers/punkt')
except LookupError:
    nltk.download('punkt')

@dataclass
class TextChunk:
    """文本塊數據類"""
    content: str
    metadata: Dict[str, Any]
    token_count: int
    chunk_id: str

class TextChunker:
    """智能文本分塊器"""
    
    def __init__(self):
        self.chunk_size = TEXT_CONFIG["max_chunk_size"]
        self.chunk_overlap = TEXT_CONFIG["chunk_overlap"]
        self.min_chunk_size = TEXT_CONFIG["min_chunk_size"]
        self.encoding = tiktoken.get_encoding("cl100k_base")  # GPT-4 tokenizer
        
    def count_tokens(self, text: str) -> int:
        """計算文本的token數量"""
        return len(self.encoding.encode(text))
    
    def split_into_sentences(self, text: str) -> List[str]:
        """將文本分割為句子"""
        # 使用NLTK進行句子分割
        sentences = nltk.sent_tokenize(text)
        
        # 清理和過濾句子
        cleaned_sentences = []
        for sentence in sentences:
            sentence = sentence.strip()
            if len(sentence) > 10:  # 過濾太短的句子
                cleaned_sentences.append(sentence)
        
        return cleaned_sentences
    
    def semantic_chunking(self, text: str, source_file: str = "") -> List[TextChunk]:
        """基於語義的智能分塊"""
        sentences = self.split_into_sentences(text)
        chunks = []
        current_chunk = ""
        current_tokens = 0
        chunk_counter = 0
        
        for i, sentence in enumerate(sentences):
            sentence_tokens = self.count_tokens(sentence)
            
            # 檢查是否需要開始新的chunk
            if (current_tokens + sentence_tokens > self.chunk_size and 
                current_chunk and 
                current_tokens >= self.min_chunk_size):
                
                # 創建當前chunk
                chunk = self._create_chunk(
                    content=current_chunk.strip(),
                    chunk_id=f"{source_file}_chunk_{chunk_counter}",
                    source_file=source_file,
                    chunk_index=chunk_counter
                )
                chunks.append(chunk)
                
                # 準備下一個chunk，包含重疊內容
                overlap_content = self._get_overlap_content(current_chunk)
                current_chunk = overlap_content + " " + sentence
                current_tokens = self.count_tokens(current_chunk)
                chunk_counter += 1
            else:
                # 添加句子到當前chunk
                if current_chunk:
                    current_chunk += " " + sentence
                else:
                    current_chunk = sentence
                current_tokens += sentence_tokens
        
        # 處理最後一個chunk
        if current_chunk.strip() and len(current_chunk.strip()) >= self.min_chunk_size:
            chunk = self._create_chunk(
                content=current_chunk.strip(),
                chunk_id=f"{source_file}_chunk_{chunk_counter}",
                source_file=source_file,
                chunk_index=chunk_counter
            )
            chunks.append(chunk)
        
        return chunks
    
    def _get_overlap_content(self, text: str) -> str:
        """獲取重疊內容"""
        if not text:
            return ""
        
        sentences = self.split_into_sentences(text)
        if len(sentences) <= 1:
            return ""
        
        # 計算需要重疊的句子數量
        overlap_sentences = []
        overlap_tokens = 0
        
        # 從後往前添加句子，直到達到重疊大小
        for sentence in reversed(sentences):
            sentence_tokens = self.count_tokens(sentence)
            if overlap_tokens + sentence_tokens <= self.chunk_overlap:
                overlap_sentences.insert(0, sentence)
                overlap_tokens += sentence_tokens
            else:
                break
        
        return " ".join(overlap_sentences)
    
    def _create_chunk(self, content: str, chunk_id: str, source_file: str, chunk_index: int) -> TextChunk:
        """創建文本塊對象"""
        token_count = self.count_tokens(content)
        
        metadata = {
            "source_file": source_file,
            "chunk_index": chunk_index,
            "char_count": len(content),
            "word_count": len(content.split()),
            "created_at": self._get_timestamp()
        }
        
        return TextChunk(
            content=content,
            metadata=metadata,
            token_count=token_count,
            chunk_id=chunk_id
        )
    
    def _get_timestamp(self) -> str:
        """獲取當前時間戳"""
        from datetime import datetime
        return datetime.now().isoformat()
    
    def fixed_size_chunking(self, text: str, source_file: str = "") -> List[TextChunk]:
        """固定大小分塊（備用方法）"""
        words = text.split()
        chunks = []
        chunk_counter = 0
        
        for i in range(0, len(words), self.chunk_size // 4):  # 假設平均每個詞4個字符
            chunk_words = words[i:i + self.chunk_size // 4]
            content = " ".join(chunk_words)
            
            if len(content) >= self.min_chunk_size:
                chunk = self._create_chunk(
                    content=content,
                    chunk_id=f"{source_file}_fixed_{chunk_counter}",
                    source_file=source_file,
                    chunk_index=chunk_counter
                )
                chunks.append(chunk)
                chunk_counter += 1
        
        return chunks
    
    def paragraph_based_chunking(self, text: str, source_file: str = "") -> List[TextChunk]:
        """基於段落的分塊"""
        paragraphs = text.split('\n\n')
        chunks = []
        current_chunk = ""
        current_tokens = 0
        chunk_counter = 0
        
        for paragraph in paragraphs:
            paragraph = paragraph.strip()
            if not paragraph:
                continue
            
            paragraph_tokens = self.count_tokens(paragraph)
            
            # 如果單個段落就超過chunk大小，需要進一步分割
            if paragraph_tokens > self.chunk_size:
                # 先保存當前chunk
                if current_chunk:
                    chunk = self._create_chunk(
                        content=current_chunk.strip(),
                        chunk_id=f"{source_file}_para_{chunk_counter}",
                        source_file=source_file,
                        chunk_index=chunk_counter
                    )
                    chunks.append(chunk)
                    chunk_counter += 1
                    current_chunk = ""
                    current_tokens = 0
                
                # 對大段落進行句子級分割
                large_para_chunks = self.semantic_chunking(paragraph, f"{source_file}_large_para")
                chunks.extend(large_para_chunks)
                chunk_counter += len(large_para_chunks)
                
            elif current_tokens + paragraph_tokens > self.chunk_size and current_chunk:
                # 保存當前chunk
                chunk = self._create_chunk(
                    content=current_chunk.strip(),
                    chunk_id=f"{source_file}_para_{chunk_counter}",
                    source_file=source_file,
                    chunk_index=chunk_counter
                )
                chunks.append(chunk)
                chunk_counter += 1
                
                # 開始新chunk
                current_chunk = paragraph
                current_tokens = paragraph_tokens
            else:
                # 添加到當前chunk
                if current_chunk:
                    current_chunk += "\n\n" + paragraph
                else:
                    current_chunk = paragraph
                current_tokens += paragraph_tokens
        
        # 處理最後一個chunk
        if current_chunk.strip():
            chunk = self._create_chunk(
                content=current_chunk.strip(),
                chunk_id=f"{source_file}_para_{chunk_counter}",
                source_file=source_file,
                chunk_index=chunk_counter
            )
            chunks.append(chunk)
        
        return chunks
    
    def chunk_text(self, text: str, source_file: str = "", method: str = "semantic") -> List[TextChunk]:
        """主要的文本分塊方法"""
        if not text or len(text.strip()) < self.min_chunk_size:
            return []
        
        # 預處理文本
        text = self._preprocess_text(text)
        
        # 根據方法選擇分塊策略
        if method == "semantic":
            return self.semantic_chunking(text, source_file)
        elif method == "paragraph":
            return self.paragraph_based_chunking(text, source_file)
        elif method == "fixed":
            return self.fixed_size_chunking(text, source_file)
        else:
            raise ValueError(f"Unknown chunking method: {method}")
    
    def _preprocess_text(self, text: str) -> str:
        """預處理文本"""
        # 移除多餘的空白字符
        text = re.sub(r'\s+', ' ', text)
        
        # 移除多餘的換行符
        text = re.sub(r'\n\s*\n', '\n\n', text)
        
        # 確保句子之間有適當的空格
        text = re.sub(r'\.([A-Z])', r'. \1', text)
        
        return text.strip()
    
    def get_chunk_statistics(self, chunks: List[TextChunk]) -> Dict[str, Any]:
        """獲取分塊統計信息"""
        if not chunks:
            return {}
        
        token_counts = [chunk.token_count for chunk in chunks]
        char_counts = [len(chunk.content) for chunk in chunks]
        
        return {
            "total_chunks": len(chunks),
            "avg_tokens_per_chunk": sum(token_counts) / len(token_counts),
            "max_tokens_per_chunk": max(token_counts),
            "min_tokens_per_chunk": min(token_counts),
            "avg_chars_per_chunk": sum(char_counts) / len(char_counts),
            "total_tokens": sum(token_counts),
            "total_chars": sum(char_counts)
        } 