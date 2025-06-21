"""
聊天記錄管理模塊
支持聊天記錄的儲存、讀取和管理
"""

import json
import os
import logging
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional
import uuid

class ChatHistoryManager:
    def __init__(self, storage_dir: str = "./data/chat_history"):
        """初始化聊天記錄管理器
        
        Args:
            storage_dir: 聊天記錄儲存目錄
        """
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.current_session_file = self.storage_dir / "current_session.json"
        self.sessions_index_file = self.storage_dir / "sessions_index.json"
        
        # 初始化會話索引
        self._init_sessions_index()
        
        logging.info(f"聊天記錄管理器初始化完成，儲存目錄: {self.storage_dir}")
    
    def _init_sessions_index(self):
        """初始化會話索引文件"""
        if not self.sessions_index_file.exists():
            self._save_sessions_index([])
    
    def _load_sessions_index(self) -> List[Dict[str, Any]]:
        """載入會話索引"""
        try:
            if self.sessions_index_file.exists():
                with open(self.sessions_index_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            return []
        except Exception as e:
            logging.error(f"載入會話索引失敗: {e}")
            return []
    
    def _save_sessions_index(self, sessions: List[Dict[str, Any]]):
        """儲存會話索引"""
        try:
            with open(self.sessions_index_file, 'w', encoding='utf-8') as f:
                json.dump(sessions, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logging.error(f"儲存會話索引失敗: {e}")
    
    def create_new_session(self) -> str:
        """創建新的聊天會話
        
        Returns:
            session_id: 新會話的ID
        """
        session_id = str(uuid.uuid4())
        timestamp = datetime.now().isoformat()
        
        # 創建會話記錄
        session_data = {
            "session_id": session_id,
            "created_at": timestamp,
            "last_updated": timestamp,
            "messages": [],
            "title": "新對話",
            "message_count": 0
        }
        
        # 儲存會話文件
        session_file = self.storage_dir / f"session_{session_id}.json"
        try:
            with open(session_file, 'w', encoding='utf-8') as f:
                json.dump(session_data, f, ensure_ascii=False, indent=2)
            
            # 更新會話索引
            sessions = self._load_sessions_index()
            sessions.append({
                "session_id": session_id,
                "created_at": timestamp,
                "last_updated": timestamp,
                "title": "新對話",
                "message_count": 0,
                "file_path": str(session_file)
            })
            self._save_sessions_index(sessions)
            
            logging.info(f"創建新會話: {session_id}")
            return session_id
            
        except Exception as e:
            logging.error(f"創建新會話失敗: {e}")
            raise
    
    def save_current_session(self, messages: List[Dict[str, Any]]) -> str:
        """儲存當前會話
        
        Args:
            messages: 聊天消息列表
            
        Returns:
            session_id: 會話ID
        """
        try:
            # 載入或創建當前會話
            current_session = self.load_current_session()
            
            if not current_session:
                session_id = self.create_new_session()
                current_session = {
                    "session_id": session_id,
                    "created_at": datetime.now().isoformat(),
                    "messages": []
                }
            else:
                session_id = current_session["session_id"]
            
            # 更新會話數據
            current_session["messages"] = messages
            current_session["last_updated"] = datetime.now().isoformat()
            current_session["message_count"] = len(messages)
            
            # 生成會話標題（使用第一條用戶消息的前30個字符）
            if messages and not current_session.get("title") or current_session.get("title") == "新對話":
                for msg in messages:
                    if msg.get("type") == "user":
                        title = msg.get("content", "")[:30]
                        if len(msg.get("content", "")) > 30:
                            title += "..."
                        current_session["title"] = title or "新對話"
                        break
            
            # 儲存當前會話文件
            with open(self.current_session_file, 'w', encoding='utf-8') as f:
                json.dump(current_session, f, ensure_ascii=False, indent=2)
            
            # 儲存到會話歷史
            session_file = self.storage_dir / f"session_{session_id}.json"
            with open(session_file, 'w', encoding='utf-8') as f:
                json.dump(current_session, f, ensure_ascii=False, indent=2)
            
            # 更新會話索引
            self._update_session_in_index(current_session)
            
            logging.info(f"儲存會話: {session_id}, 消息數: {len(messages)}")
            return session_id
            
        except Exception as e:
            logging.error(f"儲存當前會話失敗: {e}")
            raise
    
    def load_current_session(self) -> Optional[Dict[str, Any]]:
        """載入當前會話
        
        Returns:
            當前會話數據，如果不存在則返回None
        """
        try:
            if self.current_session_file.exists():
                with open(self.current_session_file, 'r', encoding='utf-8') as f:
                    session_data = json.load(f)
                    logging.info(f"載入當前會話: {session_data.get('session_id')}")
                    return session_data
            return None
        except Exception as e:
            logging.error(f"載入當前會話失敗: {e}")
            return None
    
    def load_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """載入指定會話
        
        Args:
            session_id: 會話ID
            
        Returns:
            會話數據，如果不存在則返回None
        """
        try:
            session_file = self.storage_dir / f"session_{session_id}.json"
            if session_file.exists():
                with open(session_file, 'r', encoding='utf-8') as f:
                    session_data = json.load(f)
                    logging.info(f"載入會話: {session_id}")
                    return session_data
            return None
        except Exception as e:
            logging.error(f"載入會話 {session_id} 失敗: {e}")
            return None
    
    def set_current_session(self, session_id: str) -> bool:
        """設置當前會話
        
        Args:
            session_id: 要設置為當前會話的ID
            
        Returns:
            是否成功設置
        """
        try:
            session_data = self.load_session(session_id)
            if session_data:
                with open(self.current_session_file, 'w', encoding='utf-8') as f:
                    json.dump(session_data, f, ensure_ascii=False, indent=2)
                logging.info(f"設置當前會話: {session_id}")
                return True
            return False
        except Exception as e:
            logging.error(f"設置當前會話失敗: {e}")
            return False
    
    def get_sessions_list(self) -> List[Dict[str, Any]]:
        """獲取所有會話列表
        
        Returns:
            會話列表，按最後更新時間倒序排列
        """
        try:
            sessions = self._load_sessions_index()
            # 按最後更新時間倒序排列
            sessions.sort(key=lambda x: x.get("last_updated", ""), reverse=True)
            return sessions
        except Exception as e:
            logging.error(f"獲取會話列表失敗: {e}")
            return []
    
    def delete_session(self, session_id: str) -> bool:
        """刪除會話
        
        Args:
            session_id: 要刪除的會話ID
            
        Returns:
            是否成功刪除
        """
        try:
            # 刪除會話文件
            session_file = self.storage_dir / f"session_{session_id}.json"
            if session_file.exists():
                session_file.unlink()
            
            # 從索引中移除
            sessions = self._load_sessions_index()
            sessions = [s for s in sessions if s["session_id"] != session_id]
            self._save_sessions_index(sessions)
            
            # 如果刪除的是當前會話，清空當前會話
            current_session = self.load_current_session()
            if current_session and current_session.get("session_id") == session_id:
                if self.current_session_file.exists():
                    self.current_session_file.unlink()
            
            logging.info(f"刪除會話: {session_id}")
            return True
            
        except Exception as e:
            logging.error(f"刪除會話 {session_id} 失敗: {e}")
            return False
    
    def clear_current_session(self):
        """清空當前會話"""
        try:
            if self.current_session_file.exists():
                self.current_session_file.unlink()
            logging.info("清空當前會話")
        except Exception as e:
            logging.error(f"清空當前會話失敗: {e}")
    
    def _update_session_in_index(self, session_data: Dict[str, Any]):
        """更新會話索引中的會話信息"""
        try:
            sessions = self._load_sessions_index()
            session_id = session_data["session_id"]
            
            # 查找並更新現有會話
            updated = False
            for i, session in enumerate(sessions):
                if session["session_id"] == session_id:
                    sessions[i] = {
                        "session_id": session_id,
                        "created_at": session_data.get("created_at"),
                        "last_updated": session_data.get("last_updated"),
                        "title": session_data.get("title", "新對話"),
                        "message_count": session_data.get("message_count", 0),
                        "file_path": str(self.storage_dir / f"session_{session_id}.json")
                    }
                    updated = True
                    break
            
            # 如果沒找到，添加新會話
            if not updated:
                sessions.append({
                    "session_id": session_id,
                    "created_at": session_data.get("created_at"),
                    "last_updated": session_data.get("last_updated"),
                    "title": session_data.get("title", "新對話"),
                    "message_count": session_data.get("message_count", 0),
                    "file_path": str(self.storage_dir / f"session_{session_id}.json")
                })
            
            self._save_sessions_index(sessions)
            
        except Exception as e:
            logging.error(f"更新會話索引失敗: {e}")
    
    def cleanup_old_sessions(self, keep_days: int = 30):
        """清理舊會話
        
        Args:
            keep_days: 保留天數，超過此天數的會話將被刪除
        """
        try:
            from datetime import timedelta
            
            cutoff_date = datetime.now() - timedelta(days=keep_days)
            sessions = self._load_sessions_index()
            
            sessions_to_delete = []
            for session in sessions:
                try:
                    last_updated = datetime.fromisoformat(session["last_updated"])
                    if last_updated < cutoff_date:
                        sessions_to_delete.append(session["session_id"])
                except Exception as e:
                    logging.warning(f"解析會話時間失敗: {e}")
            
            # 刪除舊會話
            deleted_count = 0
            for session_id in sessions_to_delete:
                if self.delete_session(session_id):
                    deleted_count += 1
            
            logging.info(f"清理完成，刪除了 {deleted_count} 個舊會話")
            return deleted_count
            
        except Exception as e:
            logging.error(f"清理舊會話失敗: {e}")
            return 0

# 全局聊天記錄管理器實例
chat_history_manager = ChatHistoryManager() 