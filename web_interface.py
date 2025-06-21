import streamlit as st
import os
import time
import json
from typing import Dict, Any, List
import logging

from rag_system import RAGSystem
from config import Config

# 設置頁面配置
st.set_page_config(
    page_title="本地RAG聊天機器人",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 自定義CSS
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 2rem;
    }
    .status-box {
        padding: 1rem;
        border-radius: 0.5rem;
        margin: 1rem 0;
    }
    .status-success {
        background-color: #d4edda;
        border: 1px solid #c3e6cb;
        color: #155724;
    }
    .status-error {
        background-color: #f8d7da;
        border: 1px solid #f5c6cb;
        color: #721c24;
    }
    .status-warning {
        background-color: #fff3cd;
        border: 1px solid #ffeaa7;
        color: #856404;
    }
    .chat-message {
        padding: 1rem;
        border-radius: 0.5rem;
        margin: 0.5rem 0;
    }
    .user-message {
        background-color: #e3f2fd;
        border-left: 4px solid #2196f3;
    }
    .bot-message {
        background-color: #f1f8e9;
        border-left: 4px solid #4caf50;
    }
</style>
""", unsafe_allow_html=True)

@st.cache_resource
def initialize_rag_system():
    """初始化RAG系統（使用緩存）"""
    try:
        return RAGSystem()
    except Exception as e:
        st.error(f"初始化RAG系統失敗: {e}")
        return None

def display_status_box(message: str, status_type: str = "info"):
    """顯示狀態框"""
    if status_type == "success":
        css_class = "status-success"
    elif status_type == "error":
        css_class = "status-error"
    elif status_type == "warning":
        css_class = "status-warning"
    else:
        css_class = "status-box"
    
    st.markdown(f'<div class="status-box {css_class}">{message}</div>', unsafe_allow_html=True)

def main():
    """主函數"""
    # 標題
    st.markdown('<h1 class="main-header">🤖 本地RAG聊天機器人</h1>', unsafe_allow_html=True)
    
    # 初始化RAG系統
    rag_system = initialize_rag_system()
    
    if rag_system is None:
        st.error("RAG系統初始化失敗，請檢查配置和依賴。")
        return
    
    # 側邊欄
    with st.sidebar:
        st.header("📋 系統控制")
        
        # 系統狀態
        st.subheader("系統狀態")
        status = rag_system.get_system_status()
        
        if status.get("system_ready", False):
            display_status_box("✅ 系統就緒", "success")
        else:
            display_status_box("❌ 系統未就緒", "error")
        
        st.metric("已處理文檔", status.get("processed_documents", 0))
        st.metric("向量數據庫", status.get("vector_store_stats", {}).get("total_chunks", 0))
        
        # LLM提供者信息
        providers = status.get("available_llm_providers", [])
        if providers:
            st.success(f"可用LLM: {', '.join(providers)}")
        else:
            st.warning("無可用LLM提供者")
        
        st.divider()
        
        # 文檔管理
        st.subheader("📄 文檔管理")
        
        # 文件上傳
        uploaded_file = st.file_uploader(
            "上傳PDF文檔",
            type=['pdf'],
            help="選擇要添加到知識庫的PDF文件"
        )
        
        if uploaded_file is not None:
            # 保存上傳的文件
            upload_path = os.path.join("data", "uploads", uploaded_file.name)
            os.makedirs(os.path.dirname(upload_path), exist_ok=True)
            
            with open(upload_path, "wb") as f:
                f.write(uploaded_file.getbuffer())
            
            # 處理選項
            summarize = st.checkbox("自動摘要長文檔", value=True)
            
            if st.button("處理文檔", type="primary"):
                with st.spinner("正在處理文檔..."):
                    result = rag_system.add_document(upload_path, summarize=summarize)
                
                if result["success"]:
                    st.success(result["message"])
                    st.rerun()  # 刷新頁面
                else:
                    st.error(result["message"])
        
        # 已處理文檔列表
        st.subheader("已處理文檔")
        doc_list = rag_system.get_document_list()
        
        if doc_list:
            for doc in doc_list:
                with st.expander(f"📄 {doc['filename']}"):
                    st.write(f"**處理時間**: {doc['processed_at']}")
                    st.write(f"**原始長度**: {doc['original_text_length']:,} 字符")
                    st.write(f"**分塊數量**: {doc['chunk_count']}")
                    st.write(f"**處理耗時**: {doc['processing_time']:.2f} 秒")
                    
                    if st.button(f"刪除 {doc['filename']}", key=f"delete_{doc['filename']}"):
                        result = rag_system.remove_document(doc['filename'])
                        if result["success"]:
                            st.success(result["message"])
                            st.rerun()
                        else:
                            st.error(result["message"])
        else:
            st.info("尚未處理任何文檔")
    
    # 主要內容區域
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.header("💬 聊天界面")
        
        # 初始化聊天歷史
        if "messages" not in st.session_state:
            st.session_state.messages = []
        
        # 顯示聊天歷史
        for message in st.session_state.messages:
            if message["role"] == "user":
                st.markdown(f'<div class="chat-message user-message"><strong>您:</strong> {message["content"]}</div>', unsafe_allow_html=True)
            else:
                st.markdown(f'<div class="chat-message bot-message"><strong>助手:</strong> {message["content"]}</div>', unsafe_allow_html=True)
                
                # 顯示來源信息
                if "sources" in message and message["sources"]:
                    with st.expander("📚 參考來源"):
                        for i, source in enumerate(message["sources"], 1):
                            st.write(f"**來源 {i}**: {source['source_file']} (相似度: {source['similarity']:.3f})")
                            st.write(f"預覽: {source['preview']}")
                            st.divider()
        
        # 聊天輸入
        if prompt := st.chat_input("請輸入您的問題..."):
            # 添加用戶消息
            st.session_state.messages.append({"role": "user", "content": prompt})
            
            # 顯示用戶消息
            st.markdown(f'<div class="chat-message user-message"><strong>您:</strong> {prompt}</div>', unsafe_allow_html=True)
            
            # 生成回答
            with st.spinner("正在思考..."):
                result = rag_system.query(prompt)
            
            if result["success"]:
                # 添加助手消息
                assistant_message = {
                    "role": "assistant", 
                    "content": result["answer"],
                    "sources": result.get("sources", [])
                }
                st.session_state.messages.append(assistant_message)
                
                # 顯示助手消息
                st.markdown(f'<div class="chat-message bot-message"><strong>助手:</strong> {result["answer"]}</div>', unsafe_allow_html=True)
                
                # 顯示來源信息
                if result.get("sources"):
                    with st.expander("📚 參考來源"):
                        for i, source in enumerate(result["sources"], 1):
                            st.write(f"**來源 {i}**: {source['source_file']} (相似度: {source['similarity']:.3f})")
                            st.write(f"預覽: {source['preview']}")
                            st.divider()
            else:
                st.error(f"查詢失敗: {result.get('error', '未知錯誤')}")
        
        # 清除聊天歷史
        if st.button("🗑️ 清除聊天記錄"):
            st.session_state.messages = []
            st.rerun()
    
    with col2:
        st.header("⚙️ 設置")
        
        # 查詢設置
        st.subheader("查詢設置")
        
        top_k = st.slider(
            "返回結果數量",
            min_value=1,
            max_value=10,
            value=status.get("config", {}).get("top_k", 5),
            help="每次查詢返回的相關文檔片段數量"
        )
        
        similarity_threshold = st.slider(
            "相似度閾值",
            min_value=0.0,
            max_value=1.0,
            value=status.get("config", {}).get("similarity_threshold", 0.3),
            step=0.1,
            help="只返回相似度高於此閾值的結果"
        )
        
        # 更新配置
        if st.button("更新設置"):
            config_update = {
                "top_k": top_k,
                "similarity_threshold": similarity_threshold
            }
            result = rag_system.update_config(config_update)
            if result["success"]:
                st.success("設置已更新")
            else:
                st.error(result["message"])
        
        st.divider()
        
        # 系統信息
        st.subheader("系統信息")
        
        with st.expander("詳細狀態"):
            st.json(status)
        
        # 導出數據
        if st.button("📥 導出數據"):
            export_path = f"export_{int(time.time())}.json"
            result = rag_system.export_data(export_path)
            if result["success"]:
                st.success(f"數據已導出到 {export_path}")
            else:
                st.error(result["message"])

if __name__ == "__main__":
    main() 