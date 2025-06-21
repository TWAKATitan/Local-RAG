"""
本地RAG系統配置文件
"""
import os
from pathlib import Path

# 基礎路徑配置
BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
MODELS_DIR = BASE_DIR / "models"
VECTOR_DB_DIR = BASE_DIR / "vector_db"

# 創建必要目錄
for dir_path in [DATA_DIR, MODELS_DIR, VECTOR_DB_DIR]:
    dir_path.mkdir(exist_ok=True)

# PDF處理配置
PDF_CONFIG = {
    "max_file_size_mb": 100,
    "supported_formats": [".pdf"],
    "extract_images": False,
    "extract_tables": True
}

# 文本處理配置
TEXT_CONFIG = {
    "max_chunk_size": 512,  # 最大chunk token數
    "chunk_overlap": 50,    # chunk重疊token數
    "min_chunk_size": 100,  # 最小chunk大小
    "sentence_split": True, # 按句子邊界切分
    "language": "zh"        # 主要語言
}

# 模型配置
MODELS_CONFIG = {
    # 文本精簡模型 - 使用LM Studio
    "text_summarizer": {
        "provider": "lm_studio",
        "model_name": "deepseek/deepseek-r1-0528-qwen3-8b",
        "base_url": "http://localhost:1234",
        "api_key": "lm-studio",
        "max_length": 4096,
        "temperature": 0.3
    },
    
    # 向量化模型 (Embedding) - 使用Ollama
    "embedding": {
        "provider": "ollama",
        "model_name": "nomic-embed-text",
        "base_url": "http://localhost:11434",
        "dimension": 768,  # nomic-embed-text的維度
        "normalize_embeddings": True
    },
    
    # 生成模型 - 使用LM Studio
    "llm": {
        "provider": "lm_studio",
        "model_name": "deepseek/deepseek-r1-0528-qwen3-8b",
        "base_url": "http://localhost:1234",
        "api_key": "lm-studio",
        "max_length": 4096,
        "temperature": 0.7,
        "top_p": 0.9
    }
}

# 向量數據庫配置
VECTOR_DB_CONFIG = {
    "type": "chroma",  # 或 "faiss"
    "collection_name": "pdf_documents",
    "persist_directory": str(VECTOR_DB_DIR),
    "distance_metric": "cosine",
    "embedding_model": "nomic-embed-text"  # 對應Ollama中的模型
}

# 檢索配置
RETRIEVAL_CONFIG = {
    "top_k": 5,           # 返回最相關的chunk數量
    "similarity_threshold": 0.001, # 相似度閾值 (降低以允許更多結果)
    "enable_reranking": True,       # 是否重新排序
    "max_context_length": 4000  # 最大上下文長度
}

# 系統配置
SYSTEM_CONFIG = {
    "max_concurrent_requests": 5,
    "cache_enabled": True,
    "log_level": "INFO",
    "device": "auto"  # auto, cpu, cuda
}

# 提示詞模板
PROMPTS = {
    "summarize_text": """
你是一個專業的文本編輯器。請直接輸出精簡後的文本，不要有任何思考過程、說明或前言。

任務：將以下文本精簡至原文的60-90%長度
規則：
1. 保留所有核心觀點和重要資訊
2. 移除冗餘、重複和不必要的內容
3. 合併相似的句子和段落
4. 使用更簡潔的表達方式
5. 如果原文是英文，輸出英文；如果是中文，輸出繁體中文
6. 禁止添加任何解釋、前言、後記或思考過程
7. 直接開始精簡後的內容

原文：
{text}

精簡文本：
""",
    
    "rag_answer": """
基於以下相關文檔內容，回答用戶的問題。請確保答案準確且有根據。

重要指示：
- 不要提及你是什麼模型或AI助手，例如假設你是deepseek，不要透漏自己是deepseek
- 不要說明你的技術細節或後端配置
- 直接回答問題，專注於文檔內容
- 以自然、專業的語調回答
- 回答時語言只能使用繁體中文或英文，取決於使用者使用哪個語言詢問，專有名詞可使用原文，不要使用其他語言(尤其是簡體中文)
- 如果查詢不到相關資料，請說明"我無法從上傳的文檔中找到相關資料，請重新提問"

相關文檔：
{context}

用戶問題：{question}

回答：
""",
    
    "direct_answer": """
你是一個友善的助手，請簡潔地回答以下簡單交互問題。

重要指示：
- 不要提及你是什麼模型或AI助手，也不要透漏自己是deepseek
- 不要說明你的技術細節或後端配置
- 以自然、友善的語調回答
- 只回答簡單的交互性問題（如打招呼、語言設定等）
- 對於需要專業知識的問題，請說明需要開啟文檔檢索功能
- 回答時語言只能使用繁體中文或英文，取決於使用者使用哪個語言詢問

問題：{question}

回答：
""",
    
    "system_prompt": """
你是一個專業的文檔助手，能夠基於提供的文檔內容回答問題。
請遵循以下原則：
1. 只基於提供的文檔內容回答
2. 如果文檔中沒有相關信息，請明確說明
3. 回答要準確、簡潔、有條理
4. 可以引用具體的文檔片段
5. 不要提及你是什麼模型、AI系統或技術細節，也不要透漏自己是deepseek
6. 以自然、專業的語調直接回答問題
7. 對方使用類似"Hi"、"Hello"、"你好"等問候語，請回應"你好，有什麼可以幫助你的嗎？"
8. 回答時語言只能使用繁體中文和英文，不要使用其他語言(尤其是簡體中文)
"""
} 