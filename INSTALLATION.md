# 安裝指南 (Installation Guide)

本文檔提供詳細的系統安裝和配置步驟，包含被版本控制忽略的重要文件和目錄設置。

## ⚠️ 重要提醒

由於以下文件/目錄已被 `.gitignore` 排除，需要手動創建和配置：
- `venv/` - Python虛擬環境
- `node_modules/` - Node.js依賴
- `models/` - 本地模型文件
- `*.gguf` - 模型文件
- `__pycache__/` - Python緩存（自動生成）

## 系統要求

### 硬件要求
- **CPU**: Intel i5-8400 / AMD Ryzen 5 2600 或更高
- **內存**: 16GB RAM (最低8GB)
- **存儲**: 50GB可用空間 (SSD推薦)
  - 系統代碼: ~2GB
  - Python環境: ~2GB
  - Node.js依賴: ~500MB
  - 模型文件: 20-30GB (依模型大小)
  - 數據存儲: 10-20GB (依使用量)
- **GPU**: 可選，NVIDIA RTX 3060或更高 (加速推理)

### 軟件要求
- **操作系統**: Windows 10/11, macOS 10.15+, Ubuntu 18.04+
- **Python**: 3.8 - 3.11
- **Node.js**: 16.x - 18.x
- **Git**: 最新版本

## 詳細安裝步驟

### 1. 克隆項目並檢查結構

```bash
git clone <repository-url>
cd local-rag-system

# 檢查項目結構
ls -la
```

**預期看到的文件/目錄:**
```
├── api_server.py
├── rag_system.py
├── config.py
├── requirements.txt
├── package.json
├── src/
├── public/
├── data/
└── .gitignore
```

**注意**: `venv/`, `node_modules/`, `models/` 目錄不存在是正常的，需要手動創建。

### 2. 創建Python虛擬環境

```bash
# 創建虛擬環境 (這會創建 venv/ 目錄)
python -m venv venv

# 激活虛擬環境
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate

# 確認虛擬環境激活
which python  # 應該指向 venv/bin/python 或 venv\Scripts\python.exe

# 升級pip
python -m pip install --upgrade pip

# 安裝項目依賴
pip install -r requirements.txt
```

**如果安裝失敗，嘗試以下解決方案:**

```bash
# 方案1: 使用國內鏡像
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple/

# 方案2: 單獨安裝問題包
pip install chromadb --no-deps
pip install faiss-cpu

# 方案3: 清理緩存重試
pip cache purge
pip install -r requirements.txt
```

### 3. 安裝Node.js依賴

```bash
# 安裝依賴 (這會創建 node_modules/ 目錄)
npm install

# 如果速度慢，使用國內鏡像
npm install --registry https://registry.npmmirror.com

# 或使用yarn (如果已安裝)
yarn install
```

### 4. 創建必要的數據目錄

```bash
# 創建數據目錄結構
mkdir -p data/processed
mkdir -p data/summaries  
mkdir -p data/chat_history
mkdir -p data/uploads
mkdir -p vector_db
mkdir -p models

# 驗證目錄結構
tree data/ models/ vector_db/
# 或在Windows上使用: dir data models vector_db
```

### 5. 本地LLM服務安裝

#### 5.1 LM Studio安裝

1. **下載並安裝**
   - 訪問 [LM Studio官網](https://lmstudio.ai/)
   - 下載對應操作系統的版本
   - 安裝並啟動

2. **下載模型到models目錄**
   ```
   # 在LM Studio中:
   1. 搜索: deepseek/deepseek-r1-0528-qwen3-8b
   2. 下載: GGUF格式，Q4_K_M量化版本 (推薦，約8GB)
   3. 模型會自動下載到 models/ 目錄
   ```

   **模型選擇建議:**
   - **8GB RAM**: 使用3B-4B參數模型
   - **16GB RAM**: 使用7B-8B參數模型 (推薦)
   - **32GB+ RAM**: 可使用13B+參數模型

3. **啟動服務**
   - 在LM Studio中加載模型
   - 點擊"Start Server"
   - 確認端口設置為1234
   - 測試API: `http://localhost:1234/v1/models`

#### 5.2 Ollama安裝

**Windows:**
```bash
# 方法1: 使用winget
winget install Ollama.Ollama

# 方法2: 手動下載
# 從 https://ollama.ai/download 下載安裝包
```

**macOS:**
```bash
# 方法1: 使用Homebrew
brew install ollama

# 方法2: 一鍵安裝
curl -fsSL https://ollama.ai/install.sh | sh
```

**Linux:**
```bash
# 一鍵安裝
curl -fsSL https://ollama.ai/install.sh | sh

# 或手動安裝
sudo apt-get update
sudo apt-get install ollama
```

**下載向量化模型:**
```bash
# 啟動Ollama服務 (如果未自動啟動)
ollama serve

# 下載嵌入模型 (約1.7GB)
ollama pull nomic-embed-text

# 驗證安裝
ollama list
ollama show nomic-embed-text
```

### 6. 配置文件檢查和調整

檢查 `config.py` 文件中的設置:

```python
# 確認路徑設置
BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"           # 應指向項目中的data目錄
MODELS_DIR = BASE_DIR / "models"       # 應指向項目中的models目錄
VECTOR_DB_DIR = BASE_DIR / "vector_db" # 應指向項目中的vector_db目錄

# 確認LLM服務配置
MODELS_CONFIG = {
    "llm": {
        "provider": "lm_studio",
        "base_url": "http://localhost:1234",  # LM Studio默認端口
        "model_name": "deepseek/deepseek-r1-0528-qwen3-8b",
    },
    "embedding": {
        "provider": "ollama", 
        "base_url": "http://localhost:11434", # Ollama默認端口
        "model_name": "nomic-embed-text",
    }
}
```

### 7. 系統驗證

#### 7.1 檢查Python環境

```bash
# 確認虛擬環境激活
python --version
which python

# 檢查關鍵依賴
python -c "import fastapi, chromadb, ollama; print('Python依賴檢查通過')"
```

#### 7.2 檢查Node.js環境

```bash
# 檢查Node.js版本
node --version
npm --version

# 檢查依賴安裝
npm list --depth=0
```

#### 7.3 檢查LLM服務

```bash
# 檢查LM Studio (確保已啟動並加載模型)
curl http://localhost:1234/v1/models

# 檢查Ollama
curl http://localhost:11434/api/tags

# 檢查嵌入模型
curl http://localhost:11434/api/show -d '{"name": "nomic-embed-text"}'
```

#### 7.4 檢查目錄權限

```bash
# 確認目錄可寫
touch data/test.txt && rm data/test.txt
touch vector_db/test.txt && rm vector_db/test.txt
touch models/test.txt && rm models/test.txt
```

### 8. 首次啟動測試

```bash
# 方法1: 一鍵啟動 (推薦)
python start_system.py

# 方法2: 手動啟動 (用於調試)
# 終端1:
python api_server.py

# 終端2:
npm start

# 終端3 (可選):
python cli_interface.py
```

**首次啟動檢查清單:**
- [ ] Python虛擬環境已激活
- [ ] LM Studio已啟動並加載模型
- [ ] Ollama服務正在運行
- [ ] API服務啟動成功 (端口8000)
- [ ] 前端界面啟動成功 (端口3000)
- [ ] 瀏覽器能訪問 `http://localhost:3000`

## 常見安裝問題及解決方案

### Python相關問題

**問題1: 虛擬環境創建失敗**
```bash
# 解決方案: 指定Python版本
python3.9 -m venv venv
# 或
py -3.9 -m venv venv  # Windows
```

**問題2: ChromaDB安裝失敗**
```bash
# Windows: 安裝Visual C++ Build Tools
# 下載: https://visualstudio.microsoft.com/visual-cpp-build-tools/

# macOS: 安裝Xcode命令行工具
xcode-select --install

# Linux: 安裝編譯工具
sudo apt-get install build-essential python3-dev
```

**問題3: 依賴版本衝突**
```bash
# 清理環境重新安裝
rm -rf venv/
python -m venv venv
source venv/bin/activate  # 或 venv\Scripts\activate
pip install -r requirements.txt
```

### Node.js相關問題

**問題1: npm install失敗**
```bash
# 清理緩存
npm cache clean --force
rm -rf node_modules/
rm package-lock.json
npm install
```

**問題2: 端口衝突**
```bash
# 檢查端口占用
netstat -ano | findstr :3000  # Windows
lsof -i :3000                 # macOS/Linux

# 修改端口 (在package.json中)
"scripts": {
  "start": "PORT=3001 react-scripts start"
}
```

### LLM服務問題

**問題1: LM Studio無法啟動**
- 檢查系統內存是否充足 (至少8GB可用)
- 嘗試使用更小的模型
- 確認端口1234未被佔用
- 檢查防火牆設置

**問題2: Ollama連接失敗**
```bash
# 手動啟動Ollama
ollama serve

# 檢查服務狀態
# Windows:
sc query OllamaService
# macOS/Linux:
ps aux | grep ollama

# 重新安裝模型
ollama rm nomic-embed-text
ollama pull nomic-embed-text
```

**問題3: 模型下載失敗**
```bash
# 設置代理 (如果需要)
export HTTP_PROXY=http://proxy:8080
export HTTPS_PROXY=http://proxy:8080

# 檢查磁盤空間
df -h  # Linux/macOS
dir   # Windows
```

### 目錄權限問題

**問題: 無法寫入data/vector_db目錄**
```bash
# Linux/macOS:
chmod 755 data/ vector_db/ models/
chown -R $USER data/ vector_db/ models/

# Windows: 以管理員身份運行或檢查文件夾權限
```

## 開發環境額外設置

### 代碼質量工具

```bash
# 安裝開發依賴
pip install black flake8 mypy pytest

# 代碼格式化
black .

# 代碼檢查
flake8 .
mypy .

# 運行測試
pytest tests/
```

### 前端開發工具

```bash
# 安裝額外開發工具
npm install --save-dev @types/react @types/node

# 啟動開發模式
npm run start

# 構建生產版本
npm run build
```

## 性能優化建議

### 內存優化

```python
# 在config.py中調整以適應您的硬件
TEXT_CONFIG = {
    "max_chunk_size": 256,  # 8GB RAM建議
    "chunk_overlap": 25,
}

# 16GB+ RAM可以使用
TEXT_CONFIG = {
    "max_chunk_size": 512,
    "chunk_overlap": 50,
}
```

### 磁盤空間管理

```bash
# 定期清理
rm -rf __pycache__/
npm cache clean --force
pip cache purge

# 監控磁盤使用
du -sh data/ vector_db/ models/
```

## 下一步

安裝完成後，建議：

1. 閱讀 [USAGE.md](USAGE.md) 學習基本使用
2. 查看 [API.md](API.md) 了解API接口
3. 上傳一個測試PDF文檔驗證系統功能
4. 根據使用情況調整 `config.py` 中的參數

## 技術支持

如果遇到安裝問題：

1. 檢查系統要求是否滿足
2. 確認所有必需目錄已創建
3. 查看錯誤日誌: `rag_system.log`
4. 檢查服務狀態: `curl http://localhost:8000/api/health`

---

**重要提醒**: 首次安裝需要下載大量依賴和模型文件，請確保：
- 網絡連接穩定
- 磁盤空間充足 (至少50GB)
- 有足夠的時間完成安裝 (可能需要1-2小時) 