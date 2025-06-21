#!/usr/bin/env python3
"""
RAG系統快速設置腳本
此腳本會創建必要的目錄結構和檢查環境配置
"""
import os
import sys
import subprocess
from pathlib import Path

def print_status(message, status="INFO"):
    """打印狀態信息"""
    colors = {
        "INFO": "\033[94m",
        "SUCCESS": "\033[92m", 
        "WARNING": "\033[93m",
        "ERROR": "\033[91m",
        "END": "\033[0m"
    }
    print(f"{colors.get(status, '')}{status}: {message}{colors['END']}")

def check_python_version():
    """檢查Python版本"""
    version = sys.version_info
    if version.major < 3 or (version.major == 3 and version.minor < 8):
        print_status("需要Python 3.8或更高版本", "ERROR")
        return False
    print_status(f"Python版本: {version.major}.{version.minor}.{version.micro}", "SUCCESS")
    return True

def check_node_version():
    """檢查Node.js版本"""
    try:
        result = subprocess.run(['node', '--version'], capture_output=True, text=True)
        if result.returncode == 0:
            version = result.stdout.strip()
            print_status(f"Node.js版本: {version}", "SUCCESS")
            return True
        else:
            print_status("Node.js未安裝", "ERROR")
            return False
    except FileNotFoundError:
        print_status("Node.js未安裝", "ERROR")
        return False

def create_directories():
    """創建必要的目錄結構"""
    directories = [
        "data/processed",
        "data/summaries", 
        "data/chat_history",
        "data/uploads",
        "vector_db",
        "models"
    ]
    
    print_status("創建目錄結構...", "INFO")
    for directory in directories:
        path = Path(directory)
        if not path.exists():
            path.mkdir(parents=True, exist_ok=True)
            print_status(f"創建目錄: {directory}", "SUCCESS")
        else:
            print_status(f"目錄已存在: {directory}", "INFO")

def check_virtual_env():
    """檢查是否在虛擬環境中"""
    if hasattr(sys, 'real_prefix') or (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix):
        print_status("已在虛擬環境中", "SUCCESS")
        return True
    else:
        print_status("建議使用虛擬環境", "WARNING")
        print_status("運行: python -m venv venv && source venv/bin/activate", "INFO")
        return False

def check_requirements():
    """檢查requirements.txt是否存在"""
    if Path("requirements.txt").exists():
        print_status("找到requirements.txt", "SUCCESS")
        return True
    else:
        print_status("requirements.txt不存在", "ERROR")
        return False

def check_package_json():
    """檢查package.json是否存在"""
    if Path("package.json").exists():
        print_status("找到package.json", "SUCCESS")
        return True
    else:
        print_status("package.json不存在", "ERROR")
        return False

def install_python_deps():
    """安裝Python依賴"""
    if not check_requirements():
        return False
    
    try:
        print_status("安裝Python依賴...", "INFO")
        result = subprocess.run([sys.executable, '-m', 'pip', 'install', '-r', 'requirements.txt'], 
                              capture_output=True, text=True)
        if result.returncode == 0:
            print_status("Python依賴安裝成功", "SUCCESS")
            return True
        else:
            print_status(f"Python依賴安裝失敗: {result.stderr}", "ERROR")
            return False
    except Exception as e:
        print_status(f"安裝Python依賴時出錯: {e}", "ERROR")
        return False

def install_node_deps():
    """安裝Node.js依賴"""
    if not check_package_json():
        return False
    
    try:
        print_status("安裝Node.js依賴...", "INFO")
        result = subprocess.run(['npm', 'install'], capture_output=True, text=True)
        if result.returncode == 0:
            print_status("Node.js依賴安裝成功", "SUCCESS")
            return True
        else:
            print_status(f"Node.js依賴安裝失敗: {result.stderr}", "ERROR")
            return False
    except Exception as e:
        print_status(f"安裝Node.js依賴時出錯: {e}", "ERROR")
        return False

def check_services():
    """檢查LLM服務狀態"""
    print_status("檢查LLM服務狀態...", "INFO")
    
    # 檢查LM Studio
    try:
        import requests
        response = requests.get("http://localhost:1234/v1/models", timeout=5)
        if response.status_code == 200:
            print_status("LM Studio服務正常", "SUCCESS")
        else:
            print_status("LM Studio服務異常", "WARNING")
    except:
        print_status("LM Studio服務未啟動", "WARNING")
    
    # 檢查Ollama
    try:
        response = requests.get("http://localhost:11434/api/tags", timeout=5)
        if response.status_code == 200:
            print_status("Ollama服務正常", "SUCCESS")
        else:
            print_status("Ollama服務異常", "WARNING")
    except:
        print_status("Ollama服務未啟動", "WARNING")

def main():
    """主函數"""
    print_status("RAG系統環境設置開始", "INFO")
    print("=" * 50)
    
    # 檢查基本環境
    python_ok = check_python_version()
    node_ok = check_node_version()
    
    if not python_ok:
        print_status("Python版本不符合要求，請升級到3.8+", "ERROR")
        return False
    
    # 檢查虛擬環境
    check_virtual_env()
    
    # 創建目錄
    create_directories()
    
    # 詢問是否安裝依賴
    install_deps = input("\n是否安裝Python和Node.js依賴? (y/n): ").lower().strip()
    
    if install_deps == 'y':
        if python_ok:
            install_python_deps()
        if node_ok:
            install_node_deps()
    
    # 檢查服務狀態
    check_services()
    
    print("\n" + "=" * 50)
    print_status("設置完成！", "SUCCESS")
    print_status("接下來請:", "INFO")
    print("1. 啟動LM Studio並加載模型")
    print("2. 啟動Ollama並下載nomic-embed-text模型")
    print("3. 運行: python start_system.py")
    print("\n詳細說明請查看 INSTALLATION.md")
    
    return True

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print_status("\n設置已取消", "WARNING")
    except Exception as e:
        print_status(f"設置過程中出現錯誤: {e}", "ERROR") 