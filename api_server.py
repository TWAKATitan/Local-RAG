# -*- coding: utf-8 -*-
"""
FastAPI版本的RAG系統API服務器
"""

from fastapi import FastAPI, File, UploadFile, HTTPException, Form, Depends, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from contextlib import asynccontextmanager
import os
import time
import logging
import traceback
from pathlib import Path
from werkzeug.utils import secure_filename
import json
import uuid
import hashlib
import threading
from datetime import datetime, timedelta

# 導入RAG系統組件
from rag_system import RAGSystem
from llm_manager import LLMManager
from chat_history import chat_history_manager

# 配置日誌
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 全局變量
rag_system: Optional[RAGSystem] = None
llm_manager: Optional[LLMManager] = None

# 安全的上傳狀態管理系統
class SecureUploadStateManager:
    def __init__(self):
        self.upload_states = {}  # state_id -> state_data
        self.lock = threading.Lock()
    
    def generate_secure_state_id(self) -> str:
        """生成安全的上傳狀態ID"""
        # 使用時間戳 + UUID4 + 隨機鹽值 + SHA-256哈希
        timestamp = str(int(time.time() * 1000000))  # 微秒級時間戳
        random_uuid = str(uuid.uuid4())
        salt = os.urandom(16).hex()  # 16字節隨機鹽值
        
        # 組合所有元素
        combined = f"{timestamp}-{random_uuid}-{salt}"
        
        # 使用SHA-256生成最終的狀態ID
        state_id = hashlib.sha256(combined.encode()).hexdigest()
        
        logger.info(f"生成安全上傳狀態ID: {state_id[:8]}...")
        return state_id
    
    def create_upload_state(self) -> str:
        """創建新的上傳狀態"""
        state_id = self.generate_secure_state_id()
        
        with self.lock:
            self.upload_states[state_id] = {
                'files': [],
                'created_at': datetime.now(),
                'last_accessed': datetime.now()
            }
        
        logger.info(f"創建上傳狀態: {state_id[:8]}...")
        return state_id
    
    def get_upload_state(self, state_id: str) -> Optional[Dict]:
        """獲取上傳狀態數據"""
        with self.lock:
            if state_id not in self.upload_states:
                return None
            
            state = self.upload_states[state_id]
            
            # 更新最後訪問時間
            state['last_accessed'] = datetime.now()
            return state
    
    def update_upload_state(self, state_id: str, files: List[Dict]) -> bool:
        """更新上傳狀態"""
        with self.lock:
            if state_id not in self.upload_states:
                logger.warning(f"嘗試更新不存在的上傳狀態: {state_id[:8]}...")
                return False
            
            # 更新狀態
            self.upload_states[state_id]['files'] = files
            self.upload_states[state_id]['last_accessed'] = datetime.now()
            
            logger.info(f"更新上傳狀態: {state_id[:8]}..., 文件數量: {len(files)}")
            return True
    
    def cleanup_upload_state(self, state_id: str):
        """清理指定的上傳狀態"""
        with self.lock:
            if state_id in self.upload_states:
                del self.upload_states[state_id]
                logger.info(f"清理上傳狀態: {state_id[:8]}...")
    
    def get_all_states(self) -> Dict[str, Dict]:
        """獲取所有上傳狀態（用於調試）"""
        with self.lock:
            return self.upload_states.copy()

# 創建全局上傳狀態管理器
upload_state_manager = SecureUploadStateManager()

# 配置
UPLOAD_FOLDER = "./data"
MAX_FILE_SIZE = 100 * 1024 * 1024  # 100MB
ALLOWED_EXTENSIONS = {'.pdf'}

# 確保上傳目錄存在
Path(UPLOAD_FOLDER).mkdir(parents=True, exist_ok=True)

# Pydantic模型
class QueryRequest(BaseModel):
    question: str
    top_k: Optional[int] = None
    use_rag: Optional[bool] = True  # 新增：是否使用RAG檢索，預設為True

class QueryResponse(BaseModel):
    answer: str
    sources: List[Dict[str, Any]]
    processing_time: float
    timestamp: float

class HealthResponse(BaseModel):
    llm_manager_ready: bool
    rag_system_ready: bool
    status: str
    timestamp: float

class DocumentResponse(BaseModel):
    documents: List[Dict[str, Any]]
    total: int
    timestamp: float

class UploadResponse(BaseModel):
    message: str
    filename: str
    processing_time: float
    chunks_created: int
    characters_extracted: int
    pages_processed: int
    document_id: str
    storage_status: str
    timestamp: float

class DeleteResponse(BaseModel):
    message: str
    document_id: str
    removed_items: List[str]
    details: Dict[str, Any]
    timestamp: float

class ErrorResponse(BaseModel):
    error: str
    detail: Optional[str] = None
    timestamp: float

# 依賴注入
async def get_rag_system():
    """獲取RAG系統實例"""
    if not rag_system:
        raise HTTPException(status_code=500, detail="RAG系統未初始化")
    return rag_system

async def get_llm_manager():
    """獲取LLM管理器實例"""
    if not llm_manager:
        raise HTTPException(status_code=500, detail="LLM管理器未初始化")
    return llm_manager

# 工具函數
def allowed_file(filename: str) -> bool:
    """檢查文件是否允許上傳"""
    return Path(filename).suffix.lower() in ALLOWED_EXTENSIONS

def create_error_response(error_msg: str, detail: str = None) -> ErrorResponse:
    """創建錯誤響應"""
    return ErrorResponse(
        error=error_msg,
        detail=detail,
        timestamp=time.time()
    )

# 應用生命週期管理
@asynccontextmanager
async def lifespan(app: FastAPI):
    """應用生命週期管理"""
    global rag_system, llm_manager
    
    # 啟動時初始化
    try:
        logger.info("正在初始化RAG系統...")
        rag_system = RAGSystem()
        
        logger.info("正在初始化LLM管理器...")
        llm_manager = LLMManager()
        
        logger.info("系統初始化完成")
        
    except Exception as e:
        logger.error(f"系統初始化失敗: {e}")
        logger.error(traceback.format_exc())
    
    yield
    
    # 關閉時清理
    logger.info("系統正在關閉...")

# 創建FastAPI應用
app = FastAPI(
    title="RAG智能問答系統API",
    description="基於FastAPI的本地RAG系統，支持PDF文檔處理和智能問答",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# 配置CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API端點
@app.get("/api/health", response_model=HealthResponse)
async def health_check():
    """健康檢查"""
    return HealthResponse(
        llm_manager_ready=llm_manager is not None,
        rag_system_ready=rag_system is not None,
        status="healthy",
        timestamp=time.time()
    )

@app.get("/api/status")
async def get_system_status(rag: RAGSystem = Depends(get_rag_system)):
    """獲取系統狀態"""
    try:
        status = rag.get_system_status()
        return {**status, "timestamp": time.time()}
    except Exception as e:
        logger.error(f"獲取系統狀態失敗: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/query", response_model=QueryResponse)
async def query_documents(
    request: QueryRequest,
    rag: RAGSystem = Depends(get_rag_system)
):
    """查詢文檔"""
    try:
        if not request.question.strip():
            raise HTTPException(status_code=400, detail="問題不能為空")
        
        logger.info(f"收到查詢: {request.question}, 使用RAG: {request.use_rag}")
        
        # 執行查詢
        start_time = time.time()
        result = rag.query(request.question, top_k=request.top_k, use_rag=request.use_rag)
        processing_time = time.time() - start_time
        
        if result['success']:
            logger.info(f"查詢成功，耗時: {processing_time:.2f}秒")
            return QueryResponse(
                answer=result['answer'],
                sources=result.get('sources', []),
                processing_time=round(processing_time, 2),
                timestamp=time.time()
            )
        else:
            logger.error(f"查詢失敗: {result.get('error', '未知錯誤')}")
            raise HTTPException(
                status_code=500,
                detail=result.get('error', '查詢失敗')
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"查詢處理異常: {e}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"服務器內部錯誤: {str(e)}")

@app.post("/api/upload", response_model=UploadResponse)
async def upload_document(
    file: UploadFile = File(...),
    auto_summarize: bool = Form(True),
    rag: RAGSystem = Depends(get_rag_system)
):
    """上傳文檔"""
    try:
        # 檢查文件
        if not file.filename:
            raise HTTPException(status_code=400, detail="沒有選擇文件")
        
        if not allowed_file(file.filename):
            raise HTTPException(status_code=400, detail="只支持PDF文件")
        
        # 檢查文件大小
        content = await file.read()
        if len(content) > MAX_FILE_SIZE:
            raise HTTPException(status_code=413, detail="文件太大，最大支持100MB")
        
        # 保存文件 - 處理中文文件名
        original_filename = file.filename
        
        # 使用secure_filename處理文件名，但保留擴展名
        safe_filename = secure_filename(original_filename)
        
        # 如果secure_filename移除了所有字符（比如純中文文件名），使用時間戳
        if not safe_filename or safe_filename == '':
            # 提取原始文件的擴展名
            file_ext = os.path.splitext(original_filename)[1].lower()
            if not file_ext:
                file_ext = '.pdf'  # 默認為PDF
            safe_filename = f"document{file_ext}"
        
        # 確保文件名有正確的擴展名
        if not safe_filename.lower().endswith('.pdf'):
            safe_filename = os.path.splitext(safe_filename)[0] + '.pdf'
        
        # 添加時間戳避免重複
        timestamp = str(int(time.time()))
        filename = f"{timestamp}_{safe_filename}"
        filepath = os.path.join(UPLOAD_FOLDER, filename)
        
        # 保存文件
        with open(filepath, 'wb') as f:
            f.write(content)
        
        logger.info(f"文件已保存: {filepath}")
        
        # 處理文檔
        start_time = time.time()
        result = rag.add_document(filepath, summarize=auto_summarize)
        processing_time = time.time() - start_time
        
        if result['success']:
            file_info = result.get('file_info', {})
            logger.info(f"文檔處理成功: {original_filename}，耗時: {processing_time:.2f}秒，字符數: {file_info.get('character_count', 0)}")
            
            return UploadResponse(
                message='文檔處理成功',
                filename=original_filename,  # 使用原始文件名
                processing_time=round(processing_time, 2),
                chunks_created=file_info.get('chunk_count', 0),
                characters_extracted=file_info.get('character_count', 0),
                pages_processed=file_info.get('page_count', 0),
                document_id=filename,
                storage_status='permanent',
                timestamp=time.time()
            )
        else:
            # 刪除已保存的文件
            try:
                os.remove(filepath)
            except:
                pass
            
            error_msg = result.get('error', '文檔處理失敗')
            logger.error(f"文檔處理失敗: {error_msg}")
            raise HTTPException(status_code=500, detail=error_msg)
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"上傳處理異常: {e}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"服務器內部錯誤: {str(e)}")

@app.get("/api/documents", response_model=DocumentResponse)
async def list_documents(rag: RAGSystem = Depends(get_rag_system)):
    """列出所有文檔"""
    try:
        documents = rag.list_documents()
        return DocumentResponse(
            documents=documents,
            total=len(documents),
            timestamp=time.time()
        )
    except Exception as e:
        logger.error(f"列出文檔失敗: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/documents/{document_id}", response_model=DeleteResponse)
async def delete_document(
    document_id: str,
    rag: RAGSystem = Depends(get_rag_system)
):
    """刪除文檔"""
    try:
        logger.info(f"嘗試刪除文檔: {document_id}")
        result = rag.remove_document(document_id)
        
        if result['success']:
            logger.info(f"文檔刪除成功: {document_id}")
            return DeleteResponse(
                message=result.get('message', '文檔刪除成功'),
                document_id=document_id,
                removed_items=result.get('removed_items', []),
                details=result.get('details', {}),
                timestamp=time.time()
            )
        else:
            error_msg = result.get('error', result.get('message', '文檔刪除失敗'))
            logger.error(f"文檔刪除失敗: {document_id}, 錯誤: {error_msg}")
            raise HTTPException(status_code=500, detail=error_msg)
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"刪除文檔異常: {document_id}, 錯誤: {e}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"服務器內部錯誤: {str(e)}")

@app.post("/api/test")
async def test_llm(
    prompt: str = "你好，請簡單介紹一下自己。",
    llm: LLMManager = Depends(get_llm_manager)
):
    """測試LLM連接"""
    try:
        start_time = time.time()
        response = llm.generate_text(prompt, max_tokens=100)
        processing_time = time.time() - start_time
        
        return {
            "prompt": prompt,
            "response": response,
            "processing_time": round(processing_time, 2),
            "timestamp": time.time()
        }
    except Exception as e:
        logger.error(f"LLM測試失敗: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/documents/{filename}")
async def delete_document(filename: str, force: bool = False):
    """刪除文檔（支持強制刪除）"""
    try:
        result = rag_system.remove_document(filename, force=force)
        if result["success"]:
            return result
        else:
            raise HTTPException(status_code=400, detail=result["message"])
    except Exception as e:
        logger.error(f"Error deleting document: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/maintenance/cleanup-orphaned")
async def cleanup_orphaned_data():
    """清理孤立的向量數據"""
    try:
        result = rag_system.cleanup_orphaned_data()
        return result
    except Exception as e:
        logger.error(f"Error cleaning up orphaned data: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/maintenance/check-consistency")
async def check_data_consistency():
    """檢查數據一致性"""
    try:
        result = rag_system.check_data_consistency()
        return result
    except Exception as e:
        logger.error(f"Error checking data consistency: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# 聊天記錄相關端點
@app.post("/chat/save-session")
async def save_chat_session(messages: List[Dict[str, Any]]):
    """儲存聊天會話"""
    try:
        session_id = chat_history_manager.save_current_session(messages)
        return {
            "success": True,
            "session_id": session_id,
            "message": "會話儲存成功"
        }
    except Exception as e:
        logger.error(f"儲存聊天會話失敗: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/chat/load-session")
async def load_current_chat_session():
    """載入當前聊天會話"""
    try:
        session_data = chat_history_manager.load_current_session()
        if session_data:
            return {
                "success": True,
                "session": session_data
            }
        else:
            return {
                "success": True,
                "session": None,
                "message": "沒有當前會話"
            }
    except Exception as e:
        logger.error(f"載入聊天會話失敗: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/chat/sessions")
async def get_chat_sessions():
    """獲取所有聊天會話列表"""
    try:
        sessions = chat_history_manager.get_sessions_list()
        return {
            "success": True,
            "sessions": sessions
        }
    except Exception as e:
        logger.error(f"獲取聊天會話列表失敗: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/chat/sessions/{session_id}")
async def get_chat_session(session_id: str):
    """獲取指定聊天會話"""
    try:
        session_data = chat_history_manager.load_session(session_id)
        if session_data:
            return {
                "success": True,
                "session": session_data
            }
        else:
            raise HTTPException(status_code=404, detail="會話不存在")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"載入聊天會話失敗: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/chat/sessions/{session_id}/set-current")
async def set_current_chat_session(session_id: str):
    """設置當前聊天會話"""
    try:
        success = chat_history_manager.set_current_session(session_id)
        if success:
            return {
                "success": True,
                "message": "當前會話設置成功"
            }
        else:
            raise HTTPException(status_code=404, detail="會話不存在")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"設置當前會話失敗: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/chat/sessions/{session_id}")
async def delete_chat_session(session_id: str):
    """刪除聊天會話"""
    try:
        success = chat_history_manager.delete_session(session_id)
        if success:
            return {
                "success": True,
                "message": "會話刪除成功"
            }
        else:
            raise HTTPException(status_code=404, detail="會話不存在")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"刪除聊天會話失敗: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/chat/new-session")
async def create_new_chat_session():
    """創建新的聊天會話"""
    try:
        session_id = chat_history_manager.create_new_session()
        chat_history_manager.set_current_session(session_id)
        return {
            "success": True,
            "session_id": session_id,
            "message": "新會話創建成功"
        }
    except Exception as e:
        logger.error(f"創建新會話失敗: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/chat/current-session")
async def clear_current_chat_session():
    """清空當前聊天會話"""
    try:
        chat_history_manager.clear_current_session()
        return {
            "success": True,
            "message": "當前會話已清空"
        }
    except Exception as e:
        logger.error(f"清空當前會話失敗: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# 上傳狀態管理API端點
@app.post("/api/upload-state/create")
async def create_upload_state():
    """創建安全上傳狀態"""
    try:
        state_id = upload_state_manager.create_upload_state()
        return {
            "success": True,
            "state_id": state_id,
            "message": "上傳狀態創建成功"
        }
    except Exception as e:
        logger.error(f"創建上傳狀態失敗: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/upload-state/{state_id}")
async def get_upload_state(state_id: str):
    """獲取上傳狀態"""
    try:
        state_data = upload_state_manager.get_upload_state(state_id)
        if state_data is None:
            raise HTTPException(status_code=404, detail="上傳狀態不存在或已過期")
        
        return {
            "success": True,
            "files": state_data['files'],
            "created_at": state_data['created_at'].isoformat(),
            "last_accessed": state_data['last_accessed'].isoformat()
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"獲取上傳狀態失敗: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/api/upload-state/{state_id}")
async def update_upload_state(state_id: str, files: List[Dict[str, Any]]):
    """更新上傳狀態"""
    try:
        success = upload_state_manager.update_upload_state(state_id, files)
        if not success:
            raise HTTPException(status_code=404, detail="上傳狀態不存在或已過期")
        
        return {
            "success": True,
            "message": "上傳狀態更新成功"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"更新上傳狀態失敗: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/upload-state/{state_id}")
async def delete_upload_state(state_id: str):
    """刪除上傳狀態"""
    try:
        upload_state_manager.cleanup_upload_state(state_id)
        return {
            "success": True,
            "message": "上傳狀態已刪除"
        }
    except Exception as e:
        logger.error(f"刪除上傳狀態失敗: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/upload-state/debug")
async def debug_upload_states():
    """調試：獲取所有上傳狀態（僅開發環境使用）"""
    try:
        states = upload_state_manager.get_all_states()
        return {
            "success": True,
            "states_count": len(states),
            "states": {k: {
                "files_count": len(v.get('files', [])),
                "created_at": v.get('created_at', '').isoformat() if v.get('created_at') else None,
                "last_accessed": v.get('last_accessed', '').isoformat() if v.get('last_accessed') else None
            } for k, v in states.items()}
        }
    except Exception as e:
        logger.error(f"獲取上傳狀態調試信息失敗: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# 批量刪除所有文檔的API端點
@app.delete("/api/documents/delete-all")
async def delete_all_documents(rag: RAGSystem = Depends(get_rag_system)):
    """刪除所有文檔（危險操作，僅供後端使用）"""
    try:
        logger.info("收到批量刪除所有文檔的請求")
        result = rag.remove_all_documents()
        
        if result['success']:
            logger.info(f"批量刪除成功，共刪除 {result['deleted_count']} 個文檔")
            return {
                'success': True,
                'message': result['message'],
                'total_count': result['total_count'],
                'deleted_count': result['deleted_count'],
                'failed_count': result['failed_count'],
                'deleted_files': result['deleted_files'],
                'failed_files': result['failed_files'],
                'timestamp': time.time()
            }
        else:
            error_msg = result.get('message', '批量刪除失敗')
            logger.error(f"批量刪除失敗: {error_msg}")
            raise HTTPException(status_code=500, detail=error_msg)
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"批量刪除異常: {e}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"服務器內部錯誤: {str(e)}")

# 錯誤處理
@app.exception_handler(413)
async def file_too_large_handler(request, exc):
    """文件太大錯誤處理"""
    return JSONResponse(
        status_code=413,
        content=create_error_response("文件太大，最大支持100MB").dict()
    )

@app.exception_handler(404)
async def not_found_handler(request, exc):
    """404錯誤處理"""
    return JSONResponse(
        status_code=404,
        content=create_error_response("API端點不存在").dict()
    )

@app.exception_handler(500)
async def internal_error_handler(request, exc):
    """500錯誤處理"""
    logger.error(f"內部服務器錯誤: {exc}")
    return JSONResponse(
        status_code=500,
        content=create_error_response("內部服務器錯誤").dict()
    )

if __name__ == '__main__':
    import uvicorn
    
    print("🚀 啟動RAG系統FastAPI服務器...")
    print("📡 API端點:")
    print("   - GET  /api/health        - 健康檢查")
    print("   - GET  /api/status        - 系統狀態")
    print("   - POST /api/query         - 查詢文檔")
    print("   - POST /api/upload        - 上傳文檔")
    print("   - GET  /api/documents     - 列出文檔")
    print("   - DELETE /api/documents/<id> - 刪除文檔")
    print("   - DELETE /api/documents/delete-all - 刪除所有文檔（危險操作）")
    print("   - POST /api/test          - 測試LLM")
    print("   - DELETE /documents/<filename> - 刪除文檔（支持強制刪除）")
    print("   - POST /maintenance/cleanup-orphaned - 清理孤立的向量數據")
    print("   - GET  /maintenance/check-consistency - 檢查數據一致性")
    print("   - POST /api/upload-state/create - 創建安全上傳狀態")
    print("   - GET  /api/upload-state/<id> - 獲取上傳狀態")
    print("   - PUT  /api/upload-state/<id> - 更新上傳狀態")
    print("   - DELETE /api/upload-state/<id> - 刪除上傳狀態")
    print("   - GET  /api/upload-state/debug - 調試上傳狀態信息")
    print("   - POST /chat/save-session - 儲存聊天會話")
    print("   - GET  /chat/load-session - 載入當前聊天會話")
    print("   - GET  /chat/sessions     - 獲取所有聊天會話列表")
    print("   - GET  /chat/sessions/<session_id> - 獲取指定聊天會話")
    print("   - POST /chat/sessions/<session_id>/set-current - 設置當前聊天會話")
    print("   - DELETE /chat/sessions/<session_id> - 刪除聊天會話")
    print("   - POST /chat/new-session - 創建新的聊天會話")
    print("   - DELETE /chat/current-session - 清空當前聊天會話")
    print("\n🌐 服務器地址: http://localhost:8000")
    print("📱 前端地址: http://localhost:3000")
    print("📚 API文檔: http://localhost:8000/docs")
    print("📖 ReDoc文檔: http://localhost:8000/redoc")
    print("\n按 Ctrl+C 停止服務器")
    
    uvicorn.run(
        "api_server:app",
        host="0.0.0.0",
        port=8000,
        reload=False,
        log_level="info"
    )
