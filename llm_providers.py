"""
LLM Provider Interface
Supports multiple LLM providers with unified API
"""

import os
from typing import Dict, List, Optional, Union
from abc import ABC, abstractmethod
import httpx
import json


class LLMProvider(ABC):
    """Abstract base class for LLM providers"""

    def __init__(self, api_key: str, base_url: Optional[str] = None, model: str = "", timeout: float = 300.0):
        self.api_key = api_key
        self.base_url = base_url
        self.model = model
        self.client = httpx.Client(timeout=timeout)

    @abstractmethod
    def chat(self, messages: List[Dict[str, str]], **kwargs) -> Dict:
        """Send chat completion request"""
        pass

    @abstractmethod
    def count_tokens(self, text: str) -> int:
        """Count tokens in text"""
        pass

    def __del__(self):
        if hasattr(self, 'client'):
            self.client.close()


class OpenAIProvider(LLMProvider):
    """OpenAI API provider"""

    def __init__(self, api_key: str, base_url: Optional[str] = None, model: str = "gpt-4o", timeout: float = 300.0):
        super().__init__(api_key, base_url or "https://api.openai.com/v1", model, timeout)
        self.api_key = api_key

    def chat(self, messages: List[Dict[str, str]], temperature: float = 0.3,
             max_tokens: int = 4096, json_mode: bool = False, **kwargs) -> Dict:
        """Send chat completion request to OpenAI"""
        url = f"{self.base_url}/chat/completions"

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        data = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            **kwargs
        }

        if json_mode:
            data["response_format"] = {"type": "json_object"}

        response = self.client.post(url, headers=headers, json=data)
        response.raise_for_status()
        return response.json()

    def count_tokens(self, text: str) -> int:
        """Count tokens using tiktoken"""
        try:
            import tiktoken
            encoding = tiktoken.encoding_for_model(self.model)
            return len(encoding.encode(text))
        except (ImportError, KeyError):
            # Fallback: try default cl100k_base encoding
            try:
                import tiktoken
                encoding = tiktoken.get_encoding("cl100k_base")
                return len(encoding.encode(text))
            except ImportError:
                # Final fallback: approximate 1 token ≈ 4 characters for Chinese
                return len(text) // 3


class OpenAIFormatProvider(LLMProvider):
    """Generic OpenAI-compatible API provider for third-party services"""

    def __init__(self, api_key: str, base_url: Optional[str] = None, model: str = "", timeout: float = 300.0):
        super().__init__(api_key, base_url or "https://api.openai.com/v1", model, timeout)
        self.api_key = api_key

    def chat(self, messages: List[Dict[str, str]], temperature: float = 0.3,
             max_tokens: int = 4096, json_mode: bool = False, **kwargs) -> Dict:
        """Send chat completion request to OpenAI-compatible API"""
        url = f"{self.base_url}/chat/completions"

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        data = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            **kwargs
        }

        if json_mode:
            data["response_format"] = {"type": "json_object"}

        response = self.client.post(url, headers=headers, json=data)
        response.raise_for_status()
        return response.json()

    def count_tokens(self, text: str) -> int:
        """Count tokens using cl100k_base encoding (standard for OpenAI-compatible APIs)"""
        try:
            import tiktoken
            encoding = tiktoken.get_encoding("cl100k_base")
            return len(encoding.encode(text))
        except ImportError:
            return len(text) // 3


class AnthropicProvider(LLMProvider):
    """Anthropic Claude API provider"""

    def __init__(self, api_key: str, base_url: Optional[str] = None, model: str = "claude-3-opus-20240229", timeout: float = 300.0):
        super().__init__(api_key, base_url or "https://api.anthropic.com", model, timeout)
        self.api_key = api_key

    def chat(self, messages: List[Dict[str, str]], temperature: float = 0.3,
             max_tokens: int = 4096, json_mode: bool = False, **kwargs) -> Dict:
        """Send chat completion request to Anthropic"""
        # Note: Anthropic doesn't have a direct 'json_mode' parameter like OpenAI,
        # but it's very robust at following JSON instructions.
        url = f"{self.base_url}/v1/messages"

        headers = {
            "x-api-key": self.api_key,
            "Content-Type": "application/json",
            "anthropic-version": "2023-06-01"
        }

        # Convert messages format for Anthropic
        system_msg = ""
        user_messages = []
        for msg in messages:
            if msg["role"] == "system":
                system_msg = msg["content"]
            else:
                user_messages.append(msg)

        data = {
            "model": self.model,
            "messages": user_messages,
            "system": system_msg,
            "temperature": temperature,
            "max_tokens": max_tokens,
            **kwargs
        }

        response = self.client.post(url, headers=headers, json=data)
        response.raise_for_status()
        return response.json()

    def count_tokens(self, text: str) -> int:
        """Count tokens (approximate for Claude)"""
        # Claude uses similar tokenization as OpenAI for most cases
        try:
            import tiktoken
            encoding = tiktoken.get_encoding("cl100k_base")
            return len(encoding.encode(text))
        except ImportError:
            return len(text) // 3


class DeepSeekProvider(LLMProvider):
    """DeepSeek API provider (OpenAI-compatible)"""

    def __init__(self, api_key: str, base_url: Optional[str] = None, model: str = "deepseek-chat", timeout: float = 300.0):
        super().__init__(api_key, base_url or "https://api.deepseek.com", model, timeout)
        self.api_key = api_key

    def chat(self, messages: List[Dict[str, str]], temperature: float = 0.3,
             max_tokens: int = 4096, json_mode: bool = False, **kwargs) -> Dict:
        """Send chat completion request to DeepSeek (OpenAI-compatible)"""
        url = f"{self.base_url}/chat/completions"

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        data = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            **kwargs
        }

        if json_mode:
            data["response_format"] = {"type": "json_object"}

        response = self.client.post(url, headers=headers, json=data)
        response.raise_for_status()
        return response.json()

    def count_tokens(self, text: str) -> int:
        """Count tokens (approximate)"""
        return len(text) // 3


class QwenProvider(LLMProvider):
    """Qwen (通义千问) API provider (OpenAI-compatible)"""

    def __init__(self, api_key: str, base_url: Optional[str] = None, model: str = "qwen-turbo", timeout: float = 300.0):
        super().__init__(api_key, base_url or "https://dashscope.aliyuncs.com/compatible-mode/v1", model, timeout)
        self.api_key = api_key

    def chat(self, messages: List[Dict[str, str]], temperature: float = 0.3,
             max_tokens: int = 4096, json_mode: bool = False, **kwargs) -> Dict:
        """Send chat completion request to Qwen (OpenAI-compatible)"""
        url = f"{self.base_url}/chat/completions"

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        data = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            **kwargs
        }

        if json_mode:
            data["response_format"] = {"type": "json_object"}

        response = self.client.post(url, headers=headers, json=data)
        response.raise_for_status()
        return response.json()

    def count_tokens(self, text: str) -> int:
        """Count tokens (approximate)"""
        return len(text) // 3


class GLMProvider(LLMProvider):
    """GLM (智谱 AI) API provider - OpenAI-compatible"""

    def __init__(self, api_key: str, base_url: Optional[str] = None, model: str = "glm-4", timeout: float = 300.0):
        super().__init__(api_key, base_url or "https://open.bigmodel.cn/api/paas/v4", model, timeout)
        self.api_key = api_key

    def chat(self, messages: List[Dict[str, str]], temperature: float = 0.3,
             max_tokens: int = 4096, json_mode: bool = False, **kwargs) -> Dict:
        """Send chat completion request to GLM (OpenAI-compatible)"""
        url = f"{self.base_url}/chat/completions"

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        data = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            **kwargs
        }

        if json_mode:
            data["response_format"] = {"type": "json_object"}

        response = self.client.post(url, headers=headers, json=data)
        response.raise_for_status()
        return response.json()

    def count_tokens(self, text: str) -> int:
        """Count tokens (approximate)"""
        return len(text) // 3


class OllamaProvider(LLMProvider):
    """Ollama local provider"""

    def __init__(self, api_key: str = "ollama", base_url: Optional[str] = None, model: str = "llama2", timeout: float = 300.0):
        super().__init__(api_key, base_url or "http://localhost:11434", model, timeout)
        self.api_key = api_key  # Not used by Ollama

    def chat(self, messages: List[Dict[str, str]], temperature: float = 0.3,
             max_tokens: int = 4096, json_mode: bool = False, **kwargs) -> Dict:
        """Send chat completion request to Ollama"""
        url = f"{self.base_url}/api/chat"

        # Convert messages to Ollama format
        ollama_messages = []
        for msg in messages:
            ollama_messages.append({
                "role": msg["role"],
                "content": msg["content"]
            })

        data = {
            "model": self.model,
            "messages": ollama_messages,
            "stream": False,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens
            }
        }

        if json_mode:
            data["format"] = "json"

        headers = {
            "Content-Type": "application/json"
        }

        response = self.client.post(url, headers=headers, json=data)
        response.raise_for_status()

        # Convert Ollama response to OpenAI-compatible format
        ollama_response = response.json()
        return {
            "choices": [{
                "message": {
                    "role": "assistant",
                    "content": ollama_response.get("message", {}).get("content", "")
                }
            }]
        }

    def count_tokens(self, text: str) -> int:
        """Count tokens (approximate)"""
        return len(text) // 3


def get_provider(provider_name: str, config: Dict) -> LLMProvider:
    """Factory function to get LLM provider instance"""
    providers = {
        "openai": OpenAIProvider,
        "anthropic": AnthropicProvider,
        "deepseek": DeepSeekProvider,
        "qwen": QwenProvider,
        "ollama": OllamaProvider,
        "glm": GLMProvider,
        "openai-format": OpenAIFormatProvider
    }

    provider_class = providers.get(provider_name.lower())
    if not provider_class:
        raise ValueError(
            f"Unsupported provider: {provider_name}\n"
            f"Supported providers: {', '.join(providers.keys())}\n"
            f"注: 如果您使用的 OpenAI 兼容的 API，可以配置 base_url 参数"
        )

    return provider_class(
        api_key=config.get("api_key", ""),
        base_url=config.get("base_url") or None,
        model=config.get("model", ""),
        timeout=config.get("timeout", 300.0)
    )
