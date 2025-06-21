#!/usr/bin/env python3
"""
RAG系統啟動腳本
"""

import os
import sys
import time
import subprocess
import threading
from pathlib import Path

def print_banner():
    """打印啟動橫幅"""
    print("=" * 60)
    print("🤖 本地RAG聊天機器人系統")
    print("=" * 60)
    print("📋 系統組件:")
    print("   • LM Studio (文本生成)")
    print("   • Ollama (文本嵌入)")
    print("   • Flask API (後端服務)")
    print("   • React (前端界面)")
    print("=" * 60)

def check_dependencies():
    """檢查依賴"""
    print("🔍 檢查系統依賴...")
    
    # 檢查Python包
    required_packages = [
        'flask', 'flask_cors', 'requests', 'openai', 'ollama',
        'chromadb', 'sentence_transformers', 'transformers'
    ]
    
    missing_packages = []
    for package in required_packages:
        try:
            __import__(package)
            print(f"   ✓ {package}")
        except ImportError:
            missing_packages.append(package)
            print(f"   ✗ {package} (缺失)")
    
    if missing_packages:
        print(f"\n❌ 缺少依賴包: {', '.join(missing_packages)}")
        print("請運行: pip install -r requirements.txt")
        return False
    
    print("✅ 所有Python依賴已安裝")
    return True

def check_services():
    """檢查外部服務"""
    print("\n🔍 檢查外部服務...")
    
    # 檢查LM Studio
    try:
        import requests
        response = requests.get("http://localhost:1234/v1/models", timeout=3)
        if response.status_code == 200:
            print("   ✓ LM Studio (http://localhost:1234)")
        else:
            print("   ⚠️  LM Studio 響應異常")
    except:
        print("   ✗ LM Studio (http://localhost:1234) - 請確保已啟動")
        return False
    
    # 檢查Ollama
    try:
        response = requests.get("http://localhost:11434/api/tags", timeout=3)
        if response.status_code == 200:
            print("   ✓ Ollama (http://localhost:11434)")
        else:
            print("   ⚠️  Ollama 響應異常")
    except:
        print("   ✗ Ollama (http://localhost:11434) - 請確保已啟動")
        return False
    
    print("✅ 所有外部服務正常")
    return True

def test_system():
    """測試系統"""
    print("\n🧪 測試系統組件...")
    
    try:
        # 測試LLM管理器
        from llm_manager import LLMManager
        llm_manager = LLMManager()
        
        # 測試文本生成
        response = llm_manager.generate_text("你好", max_tokens=50)
        if response:
            print("   ✓ LLM文本生成")
        else:
            print("   ✗ LLM文本生成失敗")
            return False
        
        # 測試嵌入
        embeddings = llm_manager.get_embeddings("測試文本")
        if embeddings and len(embeddings) > 0:
            print("   ✓ 文本嵌入")
        else:
            print("   ✗ 文本嵌入失敗")
            return False
        
        print("✅ 系統測試通過")
        return True
        
    except Exception as e:
        print(f"   ✗ 系統測試失敗: {e}")
        return False

def start_api_server():
    """啟動API服務器"""
    print("\n🚀 啟動API服務器...")
    try:
        subprocess.run([sys.executable, "api_server.py"], check=True)
    except KeyboardInterrupt:
        print("\n⏹️  API服務器已停止")
    except Exception as e:
        print(f"❌ API服務器啟動失敗: {e}")

def start_react_dev():
    """啟動React開發服務器"""
    print("\n🚀 啟動React開發服務器...")
    try:
        # 檢查是否已安裝Node.js依賴
        if not Path("node_modules").exists():
            print("📦 安裝Node.js依賴...")
            subprocess.run(["npm", "install"], check=True)
        
        # 啟動React開發服務器
        subprocess.run(["npm", "start"], check=True)
    except KeyboardInterrupt:
        print("\n⏹️  React開發服務器已停止")
    except Exception as e:
        print(f"❌ React開發服務器啟動失敗: {e}")

def main():
    """主函數"""
    print_banner()
    
    # 檢查依賴
    if not check_dependencies():
        return 1
    
    # 檢查服務
    if not check_services():
        print("\n⚠️  請先啟動LM Studio和Ollama服務")
        return 1
    
    # 測試系統
    if not test_system():
        print("\n❌ 系統測試失敗，請檢查配置")
        return 1
    
    print("\n🎉 系統檢查完成，準備啟動服務...")
    print("\n選擇啟動模式:")
    print("1. 只啟動API服務器 (後端)")
    print("2. 只啟動React開發服務器 (前端)")
    print("3. 同時啟動API和React服務器")
    print("4. 退出")
    
    while True:
        choice = input("\n請選擇 (1-4): ").strip()
        
        if choice == "1":
            start_api_server()
            break
        elif choice == "2":
            start_react_dev()
            break
        elif choice == "3":
            print("\n🚀 同時啟動API和React服務器...")
            print("📝 提示: 使用 Ctrl+C 停止服務")
            
            # 在新線程中啟動API服務器
            api_thread = threading.Thread(target=start_api_server, daemon=True)
            api_thread.start()
            
            # 等待一下讓API服務器啟動
            time.sleep(3)
            
            # 啟動React開發服務器（主線程）
            try:
                start_react_dev()
            except KeyboardInterrupt:
                print("\n⏹️  所有服務已停止")
            break
        elif choice == "4":
            print("👋 再見！")
            break
        else:
            print("❌ 無效選擇，請重新輸入")
    
    return 0

if __name__ == "__main__":
    try:
        exit_code = main()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n\n👋 用戶中斷，再見！")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ 啟動腳本異常: {e}")
        sys.exit(1) 