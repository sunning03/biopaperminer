"""llm_client.py — 统一 LLM 接口（优化版）

优化点：
- 连接池复用（requests.Session）
- 超时和重试优化
- 更快的云端 API 回退路径
"""
import json
import time
import requests
from typing import Optional
try:
    from openai import OpenAI
    OPENAI_SDK_AVAILABLE = True
except ImportError:
    OPENAI_SDK_AVAILABLE = False

from biopaperminer.session_pool import get_session

_pool = None  # compat: 实际使用 get_session()


class LLMClient:
    """统一 LLM 接口：输入 prompt，返回文本"""
    def chat(self, prompt: str) -> Optional[str]:
        raise NotImplementedError


class OllamaClient(LLMClient):
    """本地 Ollama，沿用原 /api/generate 接口"""

    def __init__(self, base_url: str, model: str, timeout: int = 300):
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.api_url = f"{self.base_url}/api/generate"
        self.timeout = timeout
        self._session = requests.Session()

    def chat(self, prompt: str) -> Optional[str]:
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": 0.3, "top_p": 0.9, "num_predict": 8192},
        }
        try:
            resp = self._session.post(self.api_url, json=payload, timeout=self.timeout)
            if resp.status_code == 200:
                return resp.json().get("response", "")
        except Exception as e:
            print(f"[OllamaClient] 调用失败: {e}")
        return None


class OpenAICompatibleClient(LLMClient):
    """
    统一兼容 DeepSeek / Agnes / 任何 OpenAI 协议的端点。
    优化：优先用 openai SDK + Session 连接池，原生 requests 回退。
    """

    def __init__(self, base_url: str, model: str, api_key: str,
                 timeout: int = 300, max_tokens: int = 8192):
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.api_key = api_key
        self.timeout = timeout
        self.max_tokens = max_tokens

    def chat(self, prompt: str) -> Optional[str]:
        # 优先用 openai SDK
        if OPENAI_SDK_AVAILABLE:
            try:
                client = OpenAI(api_key=self.api_key, base_url=self.base_url)
                resp = client.chat.completions.create(
                    model=self.model,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.3,
                    max_tokens=self.max_tokens,
                    stream=False,
                )
                return resp.choices[0].message.content
            except Exception as e:
                print(f"[OpenAICompatibleClient-SDK] 调用失败，回退到原生 requests: {e}")

        # 回退：原生 requests（使用连接池）
        try:
            session = get_session(self.base_url)
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json; charset=utf-8",
            }
            body = {
                "model": self.model,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.3,
                "max_tokens": self.max_tokens,
                "stream": False,
            }
            url = f"{self.base_url}/chat/completions"
            body_json = json.dumps(body, ensure_ascii=False).encode("utf-8")
            resp = session.post(url, headers=headers, data=body_json, timeout=self.timeout)
            if resp.status_code == 200:
                return resp.json()["choices"][0]["message"]["content"]
            else:
                print(f"[OpenAICompatibleClient] HTTP {resp.status_code}: {resp.text[:200]}")
        except Exception as e:
            print(f"[OpenAICompatibleClient-requests] 调用失败: {e}")
        return None


def get_llm_client() -> LLMClient:
    """根据 config.LLM_PROVIDER 工厂方法返回对应客户端"""
    from biopaperminer.config import (LLM_PROVIDER,
                                      OLLAMA_BASE_URL, OLLAMA_MODEL,
                                      DEEPSEEK_API_KEY, DEEPSEEK_BASE_URL, DEEPSEEK_MODEL,
                                      AGNES_API_KEY, AGNES_BASE_URL, AGNES_MODEL,
                                      OPENAI_COMPAT_API_KEY, OPENAI_COMPAT_BASE_URL, OPENAI_COMPAT_MODEL,
                                      LLM_TIMEOUT, LLM_MAX_TOKENS)

    if LLM_PROVIDER == "ollama":
        return OllamaClient(OLLAMA_BASE_URL, OLLAMA_MODEL, timeout=LLM_TIMEOUT)
    elif LLM_PROVIDER == "deepseek":
        return OpenAICompatibleClient(DEEPSEEK_BASE_URL, DEEPSEEK_MODEL,
                                      DEEPSEEK_API_KEY, LLM_TIMEOUT, LLM_MAX_TOKENS)
    elif LLM_PROVIDER == "agnes":
        return OpenAICompatibleClient(AGNES_BASE_URL, AGNES_MODEL,
                                      AGNES_API_KEY, LLM_TIMEOUT, LLM_MAX_TOKENS)
    elif LLM_PROVIDER == "openai_compatible":
        return OpenAICompatibleClient(OPENAI_COMPAT_BASE_URL, OPENAI_COMPAT_MODEL,
                                      OPENAI_COMPAT_API_KEY, LLM_TIMEOUT, LLM_MAX_TOKENS)
    else:
        raise ValueError(f"不支持的 LLM_PROVIDER: {LLM_PROVIDER}")
