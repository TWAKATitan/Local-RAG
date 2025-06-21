# 本地RAG系統 (Local RAG System)

一個完整的本地化檢索增強生成(RAG)系統，支持PDF文檔處理、向量搜索和智能問答。

## 系統特色

- **完全本地化**: 使用本地LLM服務(LM Studio + Ollama)，無需外部API
- **多界面支持**: Web界面、CLI命令行、API服務
- **智能文檔處理**: PDF解析、文本切分、向量化存儲
- **高效檢索**: ChromaDB向量數據庫，支持語義搜索
- **會話管理**: 完整的聊天歷史記錄和會話管理

## 系統架構

```
├── 前端界面 (React)
├── API服務 (FastAPI)
├── RAG核心引擎
│   ├── PDF處理器
│   ├── 文本切分器
│   ├── 向量存儲 (ChromaDB)
│   └── LLM管理器
├── 本地LLM服務
│   ├── LM Studio (主要推理)
│   └── Ollama (向量化)
└── 數據存儲
    ├── PDF文檔
    ├── 向量數據庫
    └── 聊天記錄
```

## 快速開始

### 1. 環境準備

**系統要求:**
- Python 3.8+
- Node.js 16+
- 8GB+ RAM
- 10GB+ 可用磁盤空間

**安裝依賴:**
```bash
# Python依賴
pip install -r requirements.txt

# Node.js依賴
npm install
```

### 2. 本地LLM服務設置(建議更換成更高階的model)

**LM Studio (主要推理引擎):**
1. 下載並安裝 [LM Studio](https://lmstudio.ai/)
2. 下載模型: `deepseek/deepseek-r1-0528-qwen3-8b`
3. 啟動本地服務器 (默認端口: 1234)

**Ollama (向量化服務):**
```bash
# 安裝Ollama
curl -fsSL https://ollama.ai/install.sh | sh

# 下載向量化模型
ollama pull nomic-embed-text
```

### 3. 配置文件

編輯 `config.py` 確認服務地址:
```python
MODELS_CONFIG = {
    "llm": {
        "base_url": "http://localhost:1234",  # LM Studio
    },
    "embedding": {
        "base_url": "http://localhost:11434", # Ollama
        "model_name": "nomic-embed-text"
    }
}
```

### 4. 啟動系統

**一鍵啟動 (推薦):**
```bash
python start_system.py
```

**手動啟動:**
```bash
# 終端1: 啟動API服務
python api_server.py

# 終端2: 啟動Web界面
npm start

# 終端3: CLI界面 (可選)
python cli_interface.py
```

## 使用指南

### Web界面使用

1. 打開瀏覽器訪問: `http://localhost:3000`
2. **上傳頁面**: 上傳PDF文檔，系統自動處理和向量化
3. **聊天頁面**: 與文檔進行智能問答

### CLI界面使用

```bash
python cli_interface.py

# 主要功能:
# 1. 添加文檔
# 2. 文檔查詢
# 3. 交互聊天
# 4. 系統管理
```

### API使用

```python
import requests

# 上傳文檔
files = {'file': open('document.pdf', 'rb')}
response = requests.post('http://localhost:8000/api/upload', files=files)

# 查詢文檔
query_data = {'question': '這個文檔講什麼？', 'use_rag': True}
response = requests.post('http://localhost:8000/api/query', json=query_data)
```

## 核心功能

### 文檔處理流程

1. **PDF解析**: 提取文本內容，支持複雜版面
2. **智能精簡**: 使用LLM對文本進行結構化處理
3. **文本切分**: 智能切分為適合檢索的文本塊
4. **向量化**: 轉換為高維向量存儲
5. **索引建立**: 建立高效的向量索引

### 查詢處理流程

1. **問題向量化**: 將用戶問題轉換為向量
2. **相似度搜索**: 在向量數據庫中找到相關文檔片段
3. **上下文構建**: 組合相關片段作為上下文
4. **智能回答**: LLM基於上下文生成回答
5. **來源追蹤**: 提供答案的文檔來源信息

### 會話管理

- **歷史記錄**: 自動保存所有對話
- **會話切換**: 支持多個獨立會話
- **上下文維護**: 保持對話連貫性

## 配置說明

### 模型配置 (`config.py`)

```python
MODELS_CONFIG = {
    # 主要推理模型
    "llm": {
        "provider": "lm_studio",
        "model_name": "deepseek/deepseek-r1-0528-qwen3-8b",
        "base_url": "http://localhost:1234",
        "temperature": 0.7
    },
    
    # 向量化模型
    "embedding": {
        "provider": "ollama",
        "model_name": "nomic-embed-text",
        "base_url": "http://localhost:11434",
        "dimension": 768
    }
}
```

### 文本處理配置

```python
TEXT_CONFIG = {
    "max_chunk_size": 512,    # 最大文本塊大小
    "chunk_overlap": 50,      # 文本塊重疊
    "min_chunk_size": 100,    # 最小文本塊大小
}
```

### 檢索配置

```python
RETRIEVAL_CONFIG = {
    "top_k": 5,                      # 檢索文檔數量
    "similarity_threshold": 0.001,   # 相似度閾值
    "enable_reranking": True         # 啟用重排序
}
```

## 文件結構

```
local-rag-system/
├── api_server.py          # FastAPI服務器
├── rag_system.py          # RAG核心引擎
├── llm_manager.py         # LLM管理器
├── vector_store.py        # 向量存儲管理
├── pdf_processor.py       # PDF處理器
├── text_chunker.py        # 文本切分器
├── chat_history.py        # 聊天記錄管理
├── cli_interface.py       # 命令行界面
├── web_interface.py       # Web界面後端
├── start_system.py        # 一鍵啟動腳本
├── config.py              # 系統配置
├── requirements.txt       # Python依賴
├── package.json           # Node.js依賴
├── src/                   # React前端源碼
│   ├── components/        # React組件
│   ├── pages/            # 頁面組件
│   └── utils/            # 工具函數
├── public/               # 靜態資源
├── data/                 # 數據目錄
│   ├── processed/        # 處理後的文本
│   ├── summaries/        # 文檔摘要
│   └── chat_history/     # 聊天記錄
└── vector_db/            # 向量數據庫
```

## 故障排除

### 常見問題

**1. LM Studio連接失敗**
- 確認LM Studio已啟動並加載模型
- 檢查端口1234是否被佔用
- 確認防火牆設置

**2. Ollama服務異常**
- 重啟Ollama服務: `ollama serve`
- 確認模型已下載: `ollama list`
- 檢查端口11434可用性

**3. 向量搜索無結果**
- 確認已上傳並處理文檔
- 檢查向量數據庫狀態
- 調整相似度閾值

**4. 內存不足**
- 減少batch_size設置
- 調整chunk_size參數
- 使用更小的模型

### 日誌檢查

```bash
# 查看系統日誌
tail -f rag_system.log

# 檢查API服務狀態
curl http://localhost:8000/api/health
```

## 性能優化

### 硬件建議

- **CPU**: 8核心以上，支持AVX指令集
- **內存**: 16GB以上 (模型加載需要8-12GB)
- **存儲**: SSD，至少50GB可用空間
- **GPU**: 可選，NVIDIA RTX 3060以上 (加速推理)

### 軟件優化

1. **模型選擇**: 根據硬件選擇合適大小的模型
2. **批處理**: 調整batch_size平衡速度和內存
3. **緩存**: 啟用向量緩存減少重複計算
4. **並發**: 適當設置API服務器的worker數量

## 開發指南

### 添加新功能

1. **新的文檔格式**: 擴展 `pdf_processor.py`
2. **新的向量數據庫**: 實現 `VectorStore` 接口
3. **新的LLM提供者**: 擴展 `LLMProvider` 類
4. **新的API端點**: 在 `api_server.py` 中添加

### 代碼結構

- **模塊化設計**: 每個功能獨立模塊
- **配置驅動**: 所有配置集中在 `config.py`
- **錯誤處理**: 完整的異常處理和日誌記錄
- **類型提示**: 使用Python類型提示增強代碼可讀性

---

**注意**: 首次使用時，模型下載和文檔處理可能需要較長時間，請耐心等待。 