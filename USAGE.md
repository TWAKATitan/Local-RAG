# 使用指南 (Usage Guide)

本文檔詳細介紹如何使用本地RAG系統的各項功能。

## 系統啟動

### 一鍵啟動 (推薦)

```bash
python start_system.py
```

這將自動啟動：
- FastAPI後端服務 (端口8000)
- React前端界面 (端口3000)
- 自動打開瀏覽器

### 手動啟動

```bash
# 終端1: 啟動後端API
python api_server.py

# 終端2: 啟動前端界面
npm start

# 終端3: CLI界面 (可選)
python cli_interface.py
```

## Web界面使用

### 訪問系統

打開瀏覽器訪問: `http://localhost:3000`

### 上傳頁面

1. **選擇文件**
   - 點擊"選擇文件"或拖拽PDF到上傳區域
   - 支持的格式：PDF
   - 最大文件大小：100MB

2. **配置選項**
   - **啟用文本精簡**: 使用LLM對文檔進行智能處理
   - **分塊大小**: 調整文本切分的粒度

3. **上傳處理**
   - 點擊"上傳文檔"開始處理
   - 查看實時處理進度
   - 等待向量化完成

4. **處理結果**
   - 查看文檔統計信息
   - 檢查切分塊數量
   - 確認向量化狀態

### 聊天頁面

1. **開始對話**
   - 在輸入框中輸入問題
   - 點擊發送或按Enter
   - 等待AI回答

2. **查看回答**
   - 查看AI生成的回答
   - 檢查引用來源
   - 查看相似度分數

3. **會話管理**
   - 查看聊天歷史
   - 創建新會話
   - 切換不同會話

4. **高級選項**
   - 調整檢索數量 (top_k)
   - 選擇RAG模式或直接問答
   - 導出對話記錄

## CLI界面使用

### 啟動CLI

```bash
python cli_interface.py
```

### 主要功能

#### 1. 添加文檔

```
選擇: 1. 添加PDF文檔
輸入PDF路徑: /path/to/document.pdf
是否啟用文本精簡 (y/n): y
```

**支持的選項:**
- 相對路徑: `data/document.pdf`
- 絕對路徑: `/full/path/to/document.pdf`
- 批量添加: 輸入目錄路徑

#### 2. 文檔查詢

```
選擇: 2. 查詢文檔
請輸入問題: 這個文檔的主要內容是什麼？
檢索數量 (默認5): 10
```

**查詢結果包含:**
- AI生成的回答
- 相關文檔片段
- 來源文件信息
- 相似度分數

#### 3. 交互聊天

```
選擇: 3. 交互式聊天
您: 請總結一下上傳的文檔
助手: [AI回答...]
您: 有什麼具體的建議嗎？
```

**聊天功能:**
- 連續對話
- 上下文記憶
- 實時回答
- 來源追蹤

#### 4. 系統管理

```
選擇: 4. 系統管理
1. 查看文檔列表
2. 刪除文檔
3. 系統狀態
4. 清理數據
```

## API使用

### 基本API調用

```python
import requests

# API基礎URL
BASE_URL = "http://localhost:8000/api"

# 檢查服務狀態
response = requests.get(f"{BASE_URL}/health")
print(response.json())
```

### 文檔上傳

```python
# 上傳PDF文檔
files = {'file': open('document.pdf', 'rb')}
data = {'summarize': True}

response = requests.post(
    f"{BASE_URL}/upload",
    files=files,
    data=data
)

result = response.json()
print(f"上傳成功: {result['message']}")
```

### 文檔查詢

```python
# 查詢文檔
query_data = {
    'question': '這個文檔講什麼內容？',
    'top_k': 5,
    'use_rag': True
}

response = requests.post(
    f"{BASE_URL}/query",
    json=query_data
)

result = response.json()
print(f"回答: {result['answer']}")
print(f"來源: {len(result['sources'])} 個文檔片段")
```

### 文檔管理

```python
# 獲取文檔列表
response = requests.get(f"{BASE_URL}/documents")
documents = response.json()

# 刪除文檔
delete_data = {'filename': 'document.pdf'}
response = requests.delete(
    f"{BASE_URL}/documents",
    json=delete_data
)
```

### 聊天會話

```python
# 創建新會話
response = requests.post(f"{BASE_URL}/chat/sessions")
session_id = response.json()['session_id']

# 發送消息
message_data = {
    'message': '你好，請介紹一下上傳的文檔',
    'session_id': session_id
}

response = requests.post(
    f"{BASE_URL}/chat/message",
    json=message_data
)

# 獲取會話歷史
response = requests.get(f"{BASE_URL}/chat/sessions/{session_id}")
history = response.json()
```

## 高級功能

### 批量文檔處理

```python
import os
from pathlib import Path

def batch_upload_documents(folder_path):
    """批量上傳文檔"""
    folder = Path(folder_path)
    
    for pdf_file in folder.glob("*.pdf"):
        print(f"處理: {pdf_file.name}")
        
        files = {'file': open(pdf_file, 'rb')}
        response = requests.post(
            f"{BASE_URL}/upload",
            files=files,
            data={'summarize': True}
        )
        
        if response.status_code == 200:
            print(f"✓ {pdf_file.name} 上傳成功")
        else:
            print(f"✗ {pdf_file.name} 上傳失敗")

# 使用示例
batch_upload_documents("./documents")
```

### 自定義查詢參數

```python
# 高級查詢配置
advanced_query = {
    'question': '關於機器學習的內容',
    'top_k': 10,                    # 檢索更多結果
    'use_rag': True,
    'similarity_threshold': 0.005,   # 調整相似度閾值
    'enable_reranking': True        # 啟用重排序
}

response = requests.post(
    f"{BASE_URL}/query",
    json=advanced_query
)
```

### 系統監控

```python
# 獲取系統狀態
response = requests.get(f"{BASE_URL}/status")
status = response.json()

print(f"文檔數量: {status['documents_count']}")
print(f"向量數量: {status['vector_count']}")
print(f"內存使用: {status['memory_usage']}")
print(f"磁盤使用: {status['disk_usage']}")
```

## 最佳實踐

### 文檔上傳建議

1. **文檔質量**
   - 使用清晰、結構化的PDF
   - 避免掃描版PDF (OCR質量差)
   - 文檔大小控制在50MB以內

2. **文本精簡**
   - 對於長文檔建議啟用精簡
   - 對於結構化文檔可以跳過精簡
   - 精簡會增加處理時間但提高檢索質量

3. **批量處理**
   - 分批上傳，避免同時處理太多文檔
   - 監控系統資源使用情況
   - 大文檔建議在空閒時間處理

### 查詢優化

1. **問題表述**
   - 使用具體、明確的問題
   - 包含關鍵詞和上下文
   - 避免過於寬泛的問題

2. **參數調整**
   - `top_k=3-5`: 一般查詢
   - `top_k=10-15`: 複雜查詢
   - 調整相似度閾值過濾無關結果

3. **結果解讀**
   - 檢查來源文檔的相關性
   - 注意相似度分數
   - 結合多個來源驗證答案

### 性能優化

1. **系統配置**
   ```python
   # 在config.py中調整
   TEXT_CONFIG = {
       "max_chunk_size": 512,  # 根據內存調整
       "chunk_overlap": 50,
   }
   
   RETRIEVAL_CONFIG = {
       "top_k": 5,            # 減少檢索數量
       "enable_reranking": False  # 關閉重排序節省時間
   }
   ```

2. **硬件優化**
   - 使用SSD存儲向量數據庫
   - 增加系統內存
   - 使用多核CPU
   - 可選：使用GPU加速

## 故障排除

### 常見問題

1. **上傳失敗**
   - 檢查文件格式和大小
   - 確認磁盤空間充足
   - 查看錯誤日誌

2. **查詢無結果**
   - 確認已上傳相關文檔
   - 調整查詢關鍵詞
   - 降低相似度閾值

3. **響應緩慢**
   - 檢查LLM服務狀態
   - 監控系統資源
   - 調整並發參數

### 日誌查看

```bash
# 查看系統日誌
tail -f rag_system.log

# 查看API日誌
tail -f api_server.log

# 查看錯誤信息
grep ERROR rag_system.log
```

## 進階用法

### 自定義提示詞

```python
# 修改llm_manager.py中的提示詞模板
CUSTOM_PROMPT = """
基於以下文檔內容回答問題，請：
1. 提供準確、詳細的回答
2. 引用具體的文檔片段
3. 如果信息不足，請明確說明

文檔內容：
{context}

問題：{question}

回答：
"""
```

### 多語言支持

```python
# 在config.py中配置
TEXT_CONFIG = {
    "language": "zh",  # 中文
    # "language": "en",  # 英文
}

# 支持的語言代碼
SUPPORTED_LANGUAGES = ["zh", "en", "ja", "ko"]
```

### 集成外部工具

```python
# 集成到現有系統
class RAGIntegration:
    def __init__(self):
        self.base_url = "http://localhost:8000/api"
    
    def ask_document(self, question, document_filter=None):
        """查詢特定文檔"""
        query_data = {
            'question': question,
            'document_filter': document_filter
        }
        
        response = requests.post(
            f"{self.base_url}/query",
            json=query_data
        )
        
        return response.json()
```

---

**提示**: 系統支持熱重載，修改配置後無需重啟即可生效。建議在生產環境中使用反向代理和負載均衡。 