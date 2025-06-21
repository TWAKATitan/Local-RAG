# API文檔 (API Documentation)

本文檔詳細說明RAG系統的REST API接口。

## 基礎信息

- **基礎URL**: `http://localhost:8000/api`
- **協議**: HTTP/HTTPS
- **數據格式**: JSON
- **編碼**: UTF-8

## 認證

當前版本不需要認證，所有API端點都是公開的。

## 通用響應格式

### 成功響應

```json
{
    "success": true,
    "data": {...},
    "message": "操作成功"
}
```

### 錯誤響應

```json
{
    "success": false,
    "error": "錯誤描述",
    "code": "ERROR_CODE",
    "detail": "詳細錯誤信息"
}
```

## API端點

### 1. 健康檢查

檢查API服務狀態。

**端點**: `GET /health`

**響應**:
```json
{
    "status": "healthy",
    "timestamp": "2024-01-01T12:00:00Z",
    "version": "1.0.0"
}
```

**示例**:
```bash
curl http://localhost:8000/api/health
```

### 2. 文檔上傳

上傳PDF文檔進行處理和向量化。

**端點**: `POST /upload`

**請求格式**: `multipart/form-data`

**參數**:
- `file` (required): PDF文件
- `summarize` (optional): 是否啟用文本精簡，默認true

**響應**:
```json
{
    "success": true,
    "message": "文檔上傳成功",
    "filename": "document.pdf",
    "processing_time": 45.2,
    "chunks_created": 25,
    "file_info": {
        "size": 1024000,
        "pages": 10,
        "character_count": 15000
    }
}
```

**示例**:
```bash
curl -X POST \
  http://localhost:8000/api/upload \
  -F "file=@document.pdf" \
  -F "summarize=true"
```

```python
import requests

files = {'file': open('document.pdf', 'rb')}
data = {'summarize': True}

response = requests.post(
    'http://localhost:8000/api/upload',
    files=files,
    data=data
)
```

### 3. 文檔查詢

基於RAG進行文檔查詢。

**端點**: `POST /query`

**請求體**:
```json
{
    "question": "這個文檔講什麼內容？",
    "top_k": 5,
    "use_rag": true
}
```

**參數說明**:
- `question` (required): 查詢問題
- `top_k` (optional): 檢索文檔片段數量，默認5
- `use_rag` (optional): 是否使用RAG，默認true

**響應**:
```json
{
    "success": true,
    "answer": "這個文檔主要討論了...",
    "sources": [
        {
            "source_file": "document.pdf",
            "chunk_index": 0,
            "similarity": 0.85,
            "preview": "文檔內容預覽..."
        }
    ],
    "processing_time": 2.3,
    "chunks_used": 3
}
```

**示例**:
```bash
curl -X POST \
  http://localhost:8000/api/query \
  -H "Content-Type: application/json" \
  -d '{
    "question": "這個文檔的主要內容是什麼？",
    "top_k": 5,
    "use_rag": true
  }'
```

```python
import requests

query_data = {
    'question': '這個文檔講什麼內容？',
    'top_k': 5,
    'use_rag': True
}

response = requests.post(
    'http://localhost:8000/api/query',
    json=query_data
)
```

### 4. 文檔管理

#### 4.1 獲取文檔列表

**端點**: `GET /documents`

**響應**:
```json
{
    "success": true,
    "documents": [
        {
            "filename": "document1.pdf",
            "upload_time": "2024-01-01T12:00:00Z",
            "size": 1024000,
            "chunks": 25,
            "status": "processed"
        }
    ],
    "total": 1
}
```

**示例**:
```bash
curl http://localhost:8000/api/documents
```

#### 4.2 刪除文檔

**端點**: `DELETE /documents`

**請求體**:
```json
{
    "filename": "document.pdf",
    "force": false
}
```

**參數說明**:
- `filename` (required): 要刪除的文件名
- `force` (optional): 強制刪除，默認false

**響應**:
```json
{
    "success": true,
    "message": "文檔刪除成功",
    "removed_items": ["向量數據", "原始文件", "處理文件"]
}
```

**示例**:
```bash
curl -X DELETE \
  http://localhost:8000/api/documents \
  -H "Content-Type: application/json" \
  -d '{"filename": "document.pdf"}'
```

### 5. 聊天會話管理

#### 5.1 創建新會話

**端點**: `POST /chat/sessions`

**響應**:
```json
{
    "success": true,
    "session_id": "sess_123456789",
    "created_at": "2024-01-01T12:00:00Z"
}
```

**示例**:
```bash
curl -X POST http://localhost:8000/api/chat/sessions
```

#### 5.2 發送消息

**端點**: `POST /chat/message`

**請求體**:
```json
{
    "message": "請介紹一下這個文檔",
    "session_id": "sess_123456789",
    "use_rag": true
}
```

**響應**:
```json
{
    "success": true,
    "response": "這個文檔主要討論了...",
    "sources": [...],
    "session_id": "sess_123456789",
    "message_id": "msg_987654321"
}
```

**示例**:
```bash
curl -X POST \
  http://localhost:8000/api/chat/message \
  -H "Content-Type: application/json" \
  -d '{
    "message": "請介紹一下這個文檔",
    "session_id": "sess_123456789"
  }'
```

#### 5.3 獲取會話歷史

**端點**: `GET /chat/sessions/{session_id}`

**響應**:
```json
{
    "success": true,
    "session_id": "sess_123456789",
    "messages": [
        {
            "id": "msg_001",
            "type": "user",
            "content": "你好",
            "timestamp": "2024-01-01T12:00:00Z"
        },
        {
            "id": "msg_002", 
            "type": "assistant",
            "content": "您好！有什麼可以幫助您的嗎？",
            "timestamp": "2024-01-01T12:00:01Z",
            "sources": [...]
        }
    ],
    "total_messages": 2
}
```

**示例**:
```bash
curl http://localhost:8000/api/chat/sessions/sess_123456789
```

#### 5.4 獲取所有會話

**端點**: `GET /chat/sessions`

**響應**:
```json
{
    "success": true,
    "sessions": [
        {
            "session_id": "sess_123456789",
            "title": "關於機器學習的討論",
            "created_at": "2024-01-01T12:00:00Z",
            "updated_at": "2024-01-01T13:00:00Z",
            "message_count": 10
        }
    ],
    "total": 1
}
```

### 6. 系統狀態

#### 6.1 獲取系統狀態

**端點**: `GET /status`

**響應**:
```json
{
    "success": true,
    "status": {
        "documents_count": 5,
        "vector_count": 125,
        "sessions_count": 3,
        "memory_usage": "2.1GB",
        "disk_usage": "15.5GB",
        "uptime": "2h 30m",
        "llm_status": "connected",
        "vector_db_status": "healthy"
    }
}
```

**示例**:
```bash
curl http://localhost:8000/api/status
```

#### 6.2 獲取系統統計

**端點**: `GET /stats`

**響應**:
```json
{
    "success": true,
    "stats": {
        "total_queries": 1250,
        "total_uploads": 45,
        "avg_response_time": 1.8,
        "most_active_documents": [
            {
                "filename": "manual.pdf",
                "query_count": 89
            }
        ],
        "daily_usage": {
            "2024-01-01": {
                "queries": 125,
                "uploads": 5
            }
        }
    }
}
```

### 7. 配置管理

#### 7.1 獲取配置

**端點**: `GET /config`

**響應**:
```json
{
    "success": true,
    "config": {
        "text_config": {
            "max_chunk_size": 512,
            "chunk_overlap": 50
        },
        "retrieval_config": {
            "top_k": 5,
            "similarity_threshold": 0.001
        },
        "models_config": {
            "llm": {
                "provider": "lm_studio",
                "model_name": "deepseek/deepseek-r1-0528-qwen3-8b"
            }
        }
    }
}
```

#### 7.2 更新配置

**端點**: `PUT /config`

**請求體**:
```json
{
    "text_config": {
        "max_chunk_size": 256
    },
    "retrieval_config": {
        "top_k": 3
    }
}
```

**響應**:
```json
{
    "success": true,
    "message": "配置更新成功",
    "updated_fields": ["text_config.max_chunk_size", "retrieval_config.top_k"]
}
```

## 錯誤代碼

| 代碼 | 說明 |
|------|------|
| `INVALID_FILE_FORMAT` | 不支持的文件格式 |
| `FILE_TOO_LARGE` | 文件大小超過限制 |
| `PROCESSING_FAILED` | 文檔處理失敗 |
| `QUERY_EMPTY` | 查詢問題為空 |
| `NO_DOCUMENTS` | 沒有上傳的文檔 |
| `SESSION_NOT_FOUND` | 會話不存在 |
| `LLM_UNAVAILABLE` | LLM服務不可用 |
| `VECTOR_DB_ERROR` | 向量數據庫錯誤 |

## 限制說明

### 文件限制
- 支持格式：PDF
- 最大文件大小：100MB
- 同時上傳文件數：1個

### 查詢限制
- 問題最大長度：1000字符
- 最大top_k值：50
- 查詢頻率：無限制

### 會話限制
- 最大會話數：無限制
- 會話超時：24小時無活動
- 消息歷史：最多保留1000條

## 最佳實踐

### 1. 錯誤處理

```python
import requests

def safe_api_call(url, **kwargs):
    try:
        response = requests.post(url, **kwargs)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"API調用失敗: {e}")
        return None
    except ValueError as e:
        print(f"JSON解析失敗: {e}")
        return None
```

### 2. 批量操作

```python
def batch_upload(file_paths):
    """批量上傳文檔"""
    results = []
    
    for file_path in file_paths:
        with open(file_path, 'rb') as f:
            files = {'file': f}
            response = requests.post(
                'http://localhost:8000/api/upload',
                files=files
            )
            results.append({
                'file': file_path,
                'success': response.status_code == 200,
                'result': response.json()
            })
    
    return results
```

### 3. 異步處理

```python
import asyncio
import aiohttp

async def async_query(session, question):
    """異步查詢"""
    async with session.post(
        'http://localhost:8000/api/query',
        json={'question': question}
    ) as response:
        return await response.json()

async def batch_queries(questions):
    """批量異步查詢"""
    async with aiohttp.ClientSession() as session:
        tasks = [async_query(session, q) for q in questions]
        return await asyncio.gather(*tasks)
```

### 4. 連接池

```python
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# 配置重試策略
retry_strategy = Retry(
    total=3,
    backoff_factor=1,
    status_forcelist=[429, 500, 502, 503, 504],
)

adapter = HTTPAdapter(max_retries=retry_strategy)
session = requests.Session()
session.mount("http://", adapter)
session.mount("https://", adapter)

# 使用會話進行API調用
response = session.post(
    'http://localhost:8000/api/query',
    json={'question': '測試問題'}
)
```

## WebSocket API (計劃中)

未來版本將支持WebSocket實時通信：

```javascript
// 計劃中的WebSocket API
const ws = new WebSocket('ws://localhost:8000/ws');

ws.onmessage = function(event) {
    const data = JSON.parse(event.data);
    console.log('收到消息:', data);
};

// 發送查詢
ws.send(JSON.stringify({
    type: 'query',
    question: '這是什麼文檔？'
}));
```

---

**注意**: API接口可能會隨版本更新而變化，請關注版本更新說明。建議在生產環境中使用API版本控制。 