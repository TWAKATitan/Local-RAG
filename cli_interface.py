#!/usr/bin/env python3
"""
本地RAG系統命令行界面
"""

import os
import sys
import argparse
import json
from typing import Dict, Any, List
import logging

from rag_system import RAGSystem

def setup_logging(verbose: bool = False):
    """設置日誌"""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('rag_cli.log'),
            logging.StreamHandler()
        ]
    )

def print_banner():
    """打印歡迎橫幅"""
    banner = """
    ╔══════════════════════════════════════════════════════════════╗
    ║                    本地RAG聊天機器人                          ║
    ║                  Local RAG Chat System                      ║
    ╚══════════════════════════════════════════════════════════════╝
    """
    print(banner)

def print_status(rag_system: RAGSystem):
    """打印系統狀態"""
    status = rag_system.get_system_status()
    
    print("\n" + "="*60)
    print("系統狀態 (System Status)")
    print("="*60)
    
    # 系統就緒狀態
    ready = status.get("system_ready", False)
    print(f"系統狀態: {'✅ 就緒' if ready else '❌ 未就緒'}")
    
    # 文檔統計
    doc_count = status.get("processed_documents", 0)
    print(f"已處理文檔: {doc_count}")
    
    # 向量數據庫統計
    vector_stats = status.get("vector_store_stats", {})
    chunk_count = vector_stats.get("total_chunks", 0)
    print(f"向量數據庫: {chunk_count} 個文本塊")
    
    # LLM提供者
    providers = status.get("available_llm_providers", [])
    if providers:
        print(f"可用LLM: {', '.join(providers)}")
    else:
        print("可用LLM: 無")
    
    # 配置信息
    config = status.get("config", {})
    print(f"分塊大小: {config.get('chunk_size', 'N/A')}")
    print(f"檢索數量: {config.get('top_k', 'N/A')}")
    print(f"相似度閾值: {config.get('similarity_threshold', 'N/A')}")
    
    print("="*60)

def add_document_interactive(rag_system: RAGSystem):
    """交互式添加文檔"""
    print("\n📄 添加PDF文檔")
    print("-" * 30)
    
    while True:
        pdf_path = input("請輸入PDF文件路徑 (或輸入 'q' 退出): ").strip()
        
        if pdf_path.lower() == 'q':
            break
        
        if not os.path.exists(pdf_path):
            print(f"❌ 文件不存在: {pdf_path}")
            continue
        
        if not pdf_path.lower().endswith('.pdf'):
            print("❌ 請選擇PDF文件")
            continue
        
        # 詢問是否摘要
        summarize_input = input("是否對長文檔進行摘要? (y/n, 默認: y): ").strip().lower()
        summarize = summarize_input != 'n'
        
        print(f"\n正在處理文檔: {os.path.basename(pdf_path)}")
        print("請稍候...")
        
        result = rag_system.add_document(pdf_path, summarize=summarize)
        
        if result["success"]:
            print(f"✅ {result['message']}")
            file_info = result["file_info"]
            print(f"   - 處理時間: {file_info['processing_time']:.2f} 秒")
            print(f"   - 原始長度: {file_info['original_text_length']:,} 字符")
            print(f"   - 分塊數量: {file_info['chunk_count']}")
        else:
            print(f"❌ {result['message']}")
        
        print()

def chat_interactive(rag_system: RAGSystem):
    """交互式聊天"""
    print("\n💬 聊天模式")
    print("-" * 30)
    print("輸入您的問題，輸入 'quit' 或 'q' 退出聊天")
    print("輸入 'clear' 清除屏幕")
    print()
    
    while True:
        try:
            question = input("您: ").strip()
            
            if question.lower() in ['quit', 'q', 'exit']:
                break
            
            if question.lower() == 'clear':
                os.system('cls' if os.name == 'nt' else 'clear')
                continue
            
            if not question:
                continue
            
            print("\n🤖 正在思考...")
            result = rag_system.query(question)
            
            if result["success"]:
                print(f"\n助手: {result['answer']}")
                
                # 顯示來源信息
                sources = result.get("sources", [])
                if sources:
                    print(f"\n📚 參考來源 ({len(sources)} 個):")
                    for i, source in enumerate(sources, 1):
                        print(f"  {i}. {source['source_file']} (相似度: {source['similarity']:.3f})")
                        print(f"     預覽: {source['preview']}")
                
                # 顯示查詢統計
                print(f"\n⏱️  查詢耗時: {result['query_time']:.2f} 秒")
                print(f"📊 使用文本塊: {result['chunks_used']}")
            else:
                print(f"\n❌ 查詢失敗: {result.get('error', '未知錯誤')}")
            
            print("\n" + "-" * 50)
            
        except KeyboardInterrupt:
            print("\n\n👋 再見!")
            break
        except Exception as e:
            print(f"\n❌ 發生錯誤: {e}")

def list_documents(rag_system: RAGSystem):
    """列出已處理的文檔"""
    doc_list = rag_system.get_document_list()
    
    if not doc_list:
        print("\n📄 尚未處理任何文檔")
        return
    
    print(f"\n📄 已處理文檔 ({len(doc_list)} 個)")
    print("-" * 60)
    
    for i, doc in enumerate(doc_list, 1):
        print(f"{i}. {doc['filename']}")
        print(f"   處理時間: {doc['processed_at']}")
        print(f"   原始長度: {doc['original_text_length']:,} 字符")
        print(f"   分塊數量: {doc['chunk_count']}")
        print(f"   處理耗時: {doc['processing_time']:.2f} 秒")
        if doc.get('summarized'):
            print(f"   已摘要: 是")
        print()

def search_documents(rag_system: RAGSystem):
    """搜索文檔"""
    print("\n🔍 搜索文檔")
    print("-" * 30)
    
    query = input("請輸入搜索關鍵詞: ").strip()
    if not query:
        print("❌ 搜索關鍵詞不能為空")
        return
    
    top_k = input("返回結果數量 (默認: 5): ").strip()
    try:
        top_k = int(top_k) if top_k else 5
    except ValueError:
        top_k = 5
    
    print(f"\n正在搜索: {query}")
    results = rag_system.search_documents(query, top_k)
    
    if not results:
        print("❌ 未找到相關結果")
        return
    
    print(f"\n📋 搜索結果 ({len(results)} 個)")
    print("-" * 60)
    
    for i, result in enumerate(results, 1):
        print(f"{i}. 來源: {result['source_file']}")
        print(f"   相似度: {result['similarity']:.3f}")
        print(f"   內容預覽: {result['content'][:200]}...")
        print()

def main():
    """主函數"""
    parser = argparse.ArgumentParser(description="本地RAG系統命令行界面")
    parser.add_argument("--config", help="配置文件路徑")
    parser.add_argument("--verbose", "-v", action="store_true", help="詳細輸出")
    parser.add_argument("--add-doc", help="添加PDF文檔")
    parser.add_argument("--query", help="直接查詢問題")
    parser.add_argument("--list-docs", action="store_true", help="列出已處理文檔")
    parser.add_argument("--search", help="搜索文檔內容")
    parser.add_argument("--status", action="store_true", help="顯示系統狀態")
    
    args = parser.parse_args()
    
    # 設置日誌
    setup_logging(args.verbose)
    
    # 打印橫幅
    print_banner()
    
    # 初始化RAG系統
    try:
        print("🚀 正在初始化RAG系統...")
        rag_system = RAGSystem(args.config)
        print("✅ RAG系統初始化成功")
    except Exception as e:
        print(f"❌ RAG系統初始化失敗: {e}")
        sys.exit(1)
    
    # 根據參數執行相應操作
    if args.status:
        print_status(rag_system)
    elif args.add_doc:
        if os.path.exists(args.add_doc):
            result = rag_system.add_document(args.add_doc)
            if result["success"]:
                print(f"✅ {result['message']}")
            else:
                print(f"❌ {result['message']}")
        else:
            print(f"❌ 文件不存在: {args.add_doc}")
    elif args.query:
        result = rag_system.query(args.query)
        if result["success"]:
            print(f"\n助手: {result['answer']}")
            sources = result.get("sources", [])
            if sources:
                print(f"\n參考來源:")
                for i, source in enumerate(sources, 1):
                    print(f"  {i}. {source['source_file']} (相似度: {source['similarity']:.3f})")
        else:
            print(f"❌ 查詢失敗: {result.get('error', '未知錯誤')}")
    elif args.list_docs:
        list_documents(rag_system)
    elif args.search:
        results = rag_system.search_documents(args.search)
        if results:
            print(f"\n搜索結果:")
            for i, result in enumerate(results, 1):
                print(f"  {i}. {result['source_file']} (相似度: {result['similarity']:.3f})")
                print(f"     {result['content'][:100]}...")
        else:
            print("❌ 未找到相關結果")
    else:
        # 交互式模式
        print_status(rag_system)
        
        while True:
            print("\n📋 請選擇操作:")
            print("1. 添加PDF文檔")
            print("2. 聊天問答")
            print("3. 列出已處理文檔")
            print("4. 搜索文檔")
            print("5. 顯示系統狀態")
            print("6. 退出")
            
            choice = input("\n請輸入選項 (1-6): ").strip()
            
            if choice == '1':
                add_document_interactive(rag_system)
            elif choice == '2':
                chat_interactive(rag_system)
            elif choice == '3':
                list_documents(rag_system)
            elif choice == '4':
                search_documents(rag_system)
            elif choice == '5':
                print_status(rag_system)
            elif choice == '6':
                print("\n👋 再見!")
                break
            else:
                print("❌ 無效選項，請重新選擇")

if __name__ == "__main__":
    main() 