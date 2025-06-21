import os
import json
import requests
import subprocess
import logging
from typing import List, Dict, Any, Optional, Union
from abc import ABC, abstractmethod
import time
from openai import OpenAI
from ollama import Client

from config import MODELS_CONFIG, PROMPTS

class LLMProvider(ABC):
    """LLM提供者抽象基類"""
    
    @abstractmethod
    def generate(self, prompt: str, max_tokens: int = 512, temperature: float = 0.7) -> str:
        """生成文本"""
        pass
    
    @abstractmethod
    def is_available(self) -> bool:
        """檢查模型是否可用"""
        pass

class OllamaProvider(LLMProvider):
    """Ollama本地LLM提供者"""
    
    def __init__(self, model_name: str, base_url: str = "http://localhost:11434"):
        self.model_name = model_name
        self.base_url = base_url
        self.client = Client(host=base_url)
        
    def generate(self, prompt: str, max_tokens: int = 512, temperature: float = 0.7) -> str:
        """使用Ollama生成文本"""
        try:
            response = self.client.generate(
                model=self.model_name,
                prompt=prompt,
                options={
                    "num_predict": max_tokens,
                    "temperature": temperature
                }
            )
            
            return response['response'].strip()
                
        except Exception as e:
            logging.error(f"Error calling Ollama: {e}")
            return ""
    
    def get_embeddings(self, text: str) -> List[float]:
        """獲取文本嵌入向量"""
        try:
            response = self.client.embeddings(
                model=self.model_name,
                prompt=text
            )
            return response['embedding']
        except Exception as e:
            logging.error(f"Error getting embeddings from Ollama: {e}")
            return []
    
    def is_available(self) -> bool:
        """檢查Ollama是否可用"""
        try:
            response = requests.get(f"{self.base_url}/api/tags", timeout=5)
            return response.status_code == 200
        except:
            return False

class LMStudioProvider(LLMProvider):
    """LM Studio本地LLM提供者"""
    
    def __init__(self, model_name: str, base_url: str = "http://localhost:1234", api_key: str = "lm-studio"):
        self.model_name = model_name
        self.base_url = base_url
        self.api_key = api_key
        self.client = OpenAI(
            base_url=f"{base_url}/v1",
            api_key=api_key
        )
        
    def generate(self, prompt: str, max_tokens: int = 512, temperature: float = 0.7) -> str:
        """使用LM Studio生成文本"""
        try:
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {"role": "user", "content": prompt}
                ],
                max_tokens=max_tokens,
                temperature=temperature
            )
            
            return response.choices[0].message.content.strip()
                
        except Exception as e:
            logging.error(f"Error calling LM Studio: {e}")
            return ""
    
    def is_available(self) -> bool:
        """檢查LM Studio是否可用"""
        try:
            response = requests.get(f"{self.base_url}/v1/models", timeout=5)
            return response.status_code == 200
        except:
            return False

class GPT4AllProvider(LLMProvider):
    """GPT4All本地LLM提供者"""
    
    def __init__(self, model_name: str, model_path: str = ""):
        self.model_name = model_name
        self.model_path = model_path
        self.model = None
        self._load_model()
        
    def _load_model(self):
        """加載GPT4All模型"""
        try:
            import gpt4all
            if self.model_path and os.path.exists(self.model_path):
                self.model = gpt4all.GPT4All(self.model_path)
            else:
                self.model = gpt4all.GPT4All(self.model_name)
            logging.info(f"GPT4All model {self.model_name} loaded successfully")
        except Exception as e:
            logging.error(f"Failed to load GPT4All model: {e}")
            self.model = None
    
    def generate(self, prompt: str, max_tokens: int = 512, temperature: float = 0.7) -> str:
        """使用GPT4All生成文本"""
        if not self.model:
            return ""
        
        try:
            response = self.model.generate(
                prompt,
                max_tokens=max_tokens,
                temp=temperature
            )
            return response.strip()
        except Exception as e:
            logging.error(f"Error generating with GPT4All: {e}")
            return ""
    
    def is_available(self) -> bool:
        """檢查GPT4All是否可用"""
        return self.model is not None

class LlamaCppProvider(LLMProvider):
    """llama.cpp本地LLM提供者"""
    
    def __init__(self, model_path: str, server_url: str = "http://localhost:8080"):
        self.model_path = model_path
        self.server_url = server_url
        self.api_url = f"{server_url}/completion"
        
    def generate(self, prompt: str, max_tokens: int = 512, temperature: float = 0.7) -> str:
        """使用llama.cpp生成文本"""
        try:
            payload = {
                "prompt": prompt,
                "n_predict": max_tokens,
                "temperature": temperature,
                "stop": ["</s>", "\n\n"]
            }
            
            response = requests.post(
                self.api_url,
                json=payload,
                timeout=120
            )
            
            if response.status_code == 200:
                result = response.json()
                return result.get("content", "").strip()
            else:
                logging.error(f"llama.cpp API error: {response.status_code}")
                return ""
                
        except Exception as e:
            logging.error(f"Error calling llama.cpp: {e}")
            return ""
    
    def is_available(self) -> bool:
        """檢查llama.cpp服務器是否可用"""
        try:
            response = requests.get(f"{self.server_url}/health", timeout=5)
            return response.status_code == 200
        except:
            return False

class LLMManager:
    """本地LLM管理器"""
    
    def __init__(self):
        self.providers: Dict[str, LLMProvider] = {}
        self.current_provider: Optional[LLMProvider] = None
        self.embedding_provider: Optional[OllamaProvider] = None
        self._initialize_providers()
        
    def _initialize_providers(self):
        """初始化所有可用的LLM提供者"""
        # 初始化LM Studio提供者（用於文本生成）
        llm_config = MODELS_CONFIG["llm"]
        if llm_config["provider"] == "lm_studio":
            lm_studio = LMStudioProvider(
                model_name=llm_config["model_name"],
                base_url=llm_config["base_url"],
                api_key=llm_config["api_key"]
            )
            if lm_studio.is_available():
                self.providers["lm_studio"] = lm_studio
                self.current_provider = lm_studio
                logging.info("LM Studio provider initialized")
            else:
                logging.warning("LM Studio is not available")
        
        # 初始化Ollama提供者（用於嵌入）
        embedding_config = MODELS_CONFIG["embedding"]
        if embedding_config["provider"] == "ollama":
            ollama = OllamaProvider(
                model_name=embedding_config["model_name"],
                base_url=embedding_config["base_url"]
            )
            if ollama.is_available():
                self.providers["ollama"] = ollama
                self.embedding_provider = ollama
                logging.info("Ollama embedding provider initialized")
            else:
                logging.warning("Ollama is not available")
        
        if not self.current_provider:
            logging.error("No LLM providers available!")
        if not self.embedding_provider:
            logging.error("No embedding provider available!")
    
    def _get_current_provider_name(self) -> str:
        """獲取當前提供者名稱"""
        for name, provider in self.providers.items():
            if provider == self.current_provider:
                return name
        return "unknown"
    
    def generate_text(self, prompt: str, max_tokens: int = 512, temperature: float = 0.7) -> str:
        """生成文本"""
        if not self.current_provider:
            logging.error("No LLM provider available")
            return ""
        
        try:
            return self.current_provider.generate(prompt, max_tokens, temperature)
        except Exception as e:
            logging.error(f"Error generating text: {e}")
            return ""
    
    def get_embeddings(self, text: str) -> List[float]:
        """獲取文本嵌入向量"""
        if not self.embedding_provider:
            logging.error("No embedding provider available")
            return []
        
        try:
            return self.embedding_provider.get_embeddings(text)
        except Exception as e:
            logging.error(f"Error getting embeddings: {e}")
            return []
    
    def summarize_text(self, text: str, max_length: int = 2000) -> str:
        """
        使用LLM精簡文本（現在處理的是預切分的塊）
        
        Args:
            text: 要精簡的文本塊
            max_length: 最大輸出長度
            
        Returns:
            精簡後的文本
        """
        try:
            # 檢查輸入長度，確保在安全範圍內
            if len(text) > 8000:  # 如果單個塊太大，先截斷
                logging.warning(f"Input text too long ({len(text)} chars), truncating to 8000 chars")
                text = text[:8000] + "..."
            
            # 根據輸入長度動態調整輸出要求
            if len(text) <= 1000:
                compression_target = "60-70%"
                max_output = min(max_length, len(text))
            elif len(text) <= 3000:
                compression_target = "50-60%"
                max_output = min(max_length, int(len(text) * 0.6))
            else:
                compression_target = "40-50%"
                max_output = min(max_length, int(len(text) * 0.5))
            
            prompt = f"""請將以下文本精簡至原長度的{compression_target}，最多{max_output}字符。

要求：
1. 保留核心信息和關鍵概念
2. 移除冗餘、重複內容
3. 合併相似表達
4. 保持原文語言（英文→英文，中文→中文）
5. 直接輸出精簡結果，不要任何說明

原文：
{text}

精簡結果："""

            response = self._call_llm(prompt)
            cleaned_response = self._clean_answer(response)
            
            # 檢查輸出長度
            if len(cleaned_response) > max_output:
                logging.warning(f"Output too long ({len(cleaned_response)} chars), truncating to {max_output}")
                cleaned_response = cleaned_response[:max_output].rsplit(' ', 1)[0] + "..."
            
            if cleaned_response and len(cleaned_response.strip()) >= 20:
                compression_ratio = len(cleaned_response) / len(text) * 100
                logging.info(f"Text summarized: {len(text)} -> {len(cleaned_response)} chars ({compression_ratio:.1f}%)")
                return cleaned_response
            else:
                logging.warning("Summarization failed or produced insufficient content")
                return text
                
        except Exception as e:
            logging.error(f"Error in summarize_text: {e}")
            return text
    
    def answer_question(self, question: str, context: str) -> str:
        """基於上下文回答問題"""
        prompt = PROMPTS["rag_answer"].format(
            context=context,
            question=question
        )
        
        answer = self.generate_text(
            prompt,
            max_tokens=MODELS_CONFIG["llm"]["max_length"],
            temperature=MODELS_CONFIG["llm"]["temperature"]
        )
        
        # 清理回答中的思考標籤
        answer = self._clean_answer(answer)
        return answer
    
    def answer_question_direct(self, question: str) -> str:
        """直接回答問題（不使用RAG檢索）
        
        僅回答簡單的交互性問題，如打招呼、語言設定等
        不回答需要專業知識的問題
        """
        # 檢查是否為簡單交互性問題
        if self._is_simple_interaction(question):
            prompt = PROMPTS.get("direct_answer", 
                "請簡潔地回答以下問題。如果這是一個需要專業知識的問題，請說明您只能回答簡單的交互性問題：\n\n問題：{question}\n\n回答：").format(question=question)
            
            answer = self.generate_text(
                prompt,
                max_tokens=200,
                temperature=0.7
            )
            
            # 清理回答
            answer = self._clean_answer(answer)
            return answer
        else:
            return "抱歉，我只能回答簡單的交互性問題（如打招呼、語言設定等）。對於需要專業知識的問題，請開啟RAG檢索功能以獲得基於文檔的回答。"
    
    def _is_simple_interaction(self, question: str) -> bool:
        """判斷是否為簡單交互性問題"""
        question_lower = question.lower().strip()
        
        # 簡單交互性問題的關鍵詞
        simple_keywords = [
            "你好", "hi", "hello", "嗨", "您好",
            "謝謝", "thank", "thanks", "感謝",
            "再見", "bye", "goodbye", "掰掰",
            "繁體中文", "簡體中文", "english", "中文", "語言",
            "怎麼樣", "如何", "怎麼用", "使用方法",
            "介紹", "自己", "是誰", "什麼",
            "可以", "能夠", "功能"
        ]
        
        # 檢查是否包含簡單交互關鍵詞
        for keyword in simple_keywords:
            if keyword in question_lower:
                return True
        
        # 檢查是否為很短的問題（通常是簡單交互）
        if len(question.strip()) <= 10:
            return True
            
        return False
    
    def _clean_answer(self, answer: str) -> str:
        """清理回答中的不需要的標籤和格式"""
        import re
        
        if not answer:
            return ""
        
        # 移除 <think> 標籤及其內容 (更強力的清理)
        answer = re.sub(r'<think>.*?</think>', '', answer, flags=re.DOTALL | re.IGNORECASE)
        answer = re.sub(r'<thinking>.*?</thinking>', '', answer, flags=re.DOTALL | re.IGNORECASE)
        
        # 移除其他可能的標籤
        answer = re.sub(r'<[^>]+>', '', answer)
        
        # 移除常見的思考開頭模式
        thinking_patterns = [
            r'^嗯，.*?[。！\n]',
            r'^好的，.*?[。！\n]',
            r'^看到.*?[。！\n]', 
            r'^用户.*?[。！\n]',
            r'^這是.*?[。！\n]',
            r'^讓我.*?[。！\n]',
            r'^我需要.*?[。！\n]',
            r'^從.*?來看.*?[。！\n]',
            r'^首先.*?分析.*?[。！\n]',
            r'^根據.*?要求.*?[。！\n]',
            r'^原文.*?[。！\n]'
        ]
        
        for pattern in thinking_patterns:
            answer = re.sub(pattern, '', answer, flags=re.IGNORECASE | re.MULTILINE)
        
        # 移除說明性文字
        explanation_patterns = [
            r'.*?精簡後的.*?[:：]',
            r'.*?整理後的.*?[:：]',
            r'.*?處理結果.*?[:：]',
            r'以下是.*?[:：]',
            r'這是.*?版本.*?[:：]',
            r'好的，這是.*?[:：]'
        ]
        
        for pattern in explanation_patterns:
            answer = re.sub(pattern, '', answer, flags=re.IGNORECASE)
        
        # 移除模型自我介紹的常見模式
        patterns_to_remove = [
            r'我是.*?模型.*?[。！\n]',
            r'我是.*?AI.*?[。！\n]',
            r'我是.*?助手.*?[。！\n]',
            r'我是.*?DeepSeek.*?[。！\n]',
            r'我是.*?GPT.*?[。！\n]',
            r'我是.*?語言模型.*?[。！\n]',
            r'我是.*?人工智能.*?[。！\n]',
            r'我目前是透過.*?模型運作.*?[。！\n]',
            r'如果你使用的是.*?界面.*?[。！\n]',
            r'我可以更流暢地.*?[。！\n]',
            r'很高興你來詢問.*?[。！\n]',
            r'以下是關於我能做什麼.*?[。！\n]',
            r'相關檔案資訊的說明.*?[。！\n]'
        ]
        
        for pattern in patterns_to_remove:
            answer = re.sub(pattern, '', answer, flags=re.IGNORECASE)
        
        # 移除開頭的問候語如果包含模型信息
        greeting_patterns = [
            r'^嗨！很高興你來詢問.*?[。！\n]',
            r'^你好！我是.*?[。！\n]',
            r'^我是.*?[。！\n]'
        ]
        
        for pattern in greeting_patterns:
            answer = re.sub(pattern, '', answer, flags=re.IGNORECASE)
        
        # 清理多餘的空白和分隔符號
        answer = re.sub(r'\n\s*\n', '\n\n', answer)
        answer = re.sub(r'^[\s\n=\-*]+', '', answer)  # 移除開頭的空白和分隔符
        answer = answer.strip()
        
        # 如果答案為空或太短，返回默認回答
        if len(answer.strip()) < 10:
            return "抱歉，我無法基於提供的文檔內容回答這個問題。"
        
        return answer
    
    def extract_key_info(self, text: str) -> str:
        """提取關鍵信息"""
        prompt = f"請提取以下文本的關鍵信息：\n\n{text}\n\n關鍵信息："
        
        return self.generate_text(
            prompt,
            max_tokens=300,
            temperature=0.3
        )
    
    def switch_provider(self, provider_name: str) -> bool:
        """切換LLM提供者"""
        if provider_name in self.providers:
            self.current_provider = self.providers[provider_name]
            logging.info(f"Switched to LLM provider: {provider_name}")
            return True
        else:
            logging.error(f"Provider {provider_name} not available")
            return False
    
    def get_available_providers(self) -> List[str]:
        """獲取可用的提供者列表"""
        return list(self.providers.keys())
    
    def get_provider_status(self) -> Dict[str, Dict[str, Any]]:
        """獲取所有提供者的狀態"""
        status = {}
        for name, provider in self.providers.items():
            status[name] = {
                "available": provider.is_available(),
                "current": provider == self.current_provider,
                "type": type(provider).__name__
            }
        return status
    
    def test_generation(self, test_prompt: str = "你好，請簡單介紹一下自己。") -> Dict[str, str]:
        """測試所有可用提供者的生成能力"""
        results = {}
        for name, provider in self.providers.items():
            try:
                response = provider.generate(test_prompt, max_tokens=100, temperature=0.7)
                results[name] = response if response else "No response"
            except Exception as e:
                results[name] = f"Error: {str(e)}"
        return results

    def _call_llm(self, prompt: str, max_tokens: int = 2000, temperature: float = 0.3) -> str:
        """
        統一的 LLM 調用方法
        
        Args:
            prompt: 提示詞
            max_tokens: 最大 token 數
            temperature: 溫度參數
            
        Returns:
            LLM 回應
        """
        return self.generate_text(
            prompt,
            max_tokens=max_tokens,
            temperature=temperature
        ) 