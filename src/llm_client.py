"""轻量级 LLM HTTP 客户端 — 替代 anthropic 库，直接调用本地大模型 API。

支持 Anthropic 兼容格式（messages API），包括文本和图片（base64）输入。
无需安装 anthropic Python 包。
"""
from __future__ import annotations

import base64
import json
import os
from typing import Optional, List, Dict, Any

import httpx


class LlmClientError(Exception):
    """LLM 客户端异常"""
    pass


class LlmClient:
    """通过 HTTP 直接调用本地大模型（Anthropic 兼容 API）。

    Args:
        base_url: API 基础地址，如 http://192.168.231.1:1235
        api_key: API 密钥（默认为 lmstudio）
        model: 模型名称
    """

    def __init__(
        self,
        base_url: str = None,
        api_key: str = None,
        model: str = None,
    ):
        self.base_url = (
            base_url
            or os.environ.get("ANTHROPIC_BASE_URL", "http://192.168.231.1:1235")
        ).rstrip("/")
        self.api_key = api_key or os.environ.get("ANTHROPIC_AUTH_TOKEN", "lmstudio")
        self.model = model or os.environ.get("LLM_MODEL", "qwen/qwen3.6-27b")
        self._client: Optional[httpx.Client] = None

    def start(self):
        """启动 HTTP 客户端连接池。"""
        self._client = httpx.Client(timeout=120.0)

    def stop(self):
        """关闭 HTTP 客户端。"""
        if self._client is not None:
            self._client.close()
            self._client = None

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, *args):
        self.stop()

    def messages_create(
        self,
        *,
        model: str = None,
        max_tokens: int = 4096,
        system: str = "",
        messages: List[Dict[str, Any]],
        temperature: float = 0.1,
        top_p: float = 0.99,
    ) -> "LlmResponse":
        """发送 messages 请求（兼容 Anthropic messages API 格式）。

        Args:
            model: 模型名称，不传则用初始化时的默认值
            max_tokens: 最大输出 token 数
            system: 系统提示词
            messages: 消息列表，支持文本和图片（base64）
            temperature: 温度参数
            top_p: top_p 参数

        Returns:
            LlmResponse 对象
        """
        if self._client is None:
            raise RuntimeError("请先调用 start() 初始化客户端")

        url = f"{self.base_url}/v1/messages"
        headers = {
            "Content-Type": "application/json",
            "x-api-key": self.api_key,
        }

        # 构建请求体 — 兼容 Anthropic 格式
        body = {
            "model": model or self.model,
            "max_tokens": max_tokens,
            "messages": messages,
            "temperature": temperature,
        }
        if top_p is not None:
            body["top_p"] = top_p
        if system:
            body["system"] = system

        resp = self._client.post(url, json=body, headers=headers)

        if resp.status_code != 200:
            raise LlmClientError(
                f"LLM API 返回错误 (HTTP {resp.status_code}): {resp.text[:500]}"
            )

        data = resp.json()
        return LlmResponse(data)

    def test_connection(self) -> bool:
        """测试 API 连接是否正常。"""
        try:
            with httpx.Client(timeout=10.0) as client:
                url = f"{self.base_url}/v1/messages"
                resp = client.post(
                    url,
                    json={
                        "model": self.model,
                        "max_tokens": 16,
                        "messages": [{"role": "user", "content": "Hi"}],
                        "temperature": 0.1,
                    },
                    headers={"Content-Type": "application/json", "x-api-key": self.api_key},
                )
                return resp.status_code == 200
        except Exception:
            return False


class LlmResponse:
    """LLM API 响应的轻量包装，兼容 anthropic 库的 response 接口。"""

    def __init__(self, data: Dict[str, Any]):
        self._data = data

    @property
    def content(self) -> List["_ContentBlock"]:
        return [_ContentBlock(block) for block in self._data.get("content", [])]

    @property
    def stop_reason(self) -> Optional[str]:
        return self._data.get("stop_reason")

    @property
    def model(self) -> Optional[str]:
        return self._data.get("model")


class _ContentBlock:
    """单个内容块。"""

    def __init__(self, data: Dict[str, Any]):
        self._data = data

    @property
    def type(self) -> str:
        return self._data.get("type", "text")

    @property
    def text(self) -> str:
        return self._data.get("text", "")


# ---------------------------------------------------------------------------
# 异步版本 — 用于 FastAPI 路由
# ---------------------------------------------------------------------------

async def llm_messages_create_async(
    *,
    base_url: str,
    api_key: str,
    model: str,
    max_tokens: int = 4096,
    system: str = "",
    messages: List[Dict[str, Any]],
    temperature: float = 0.1,
) -> dict:
    """异步发送 LLM 请求，返回原始 JSON 数据。

    适用于 FastAPI 异步路由中直接调用。
    """
    url = f"{base_url.rstrip('/')}/v1/messages"
    headers = {
        "Content-Type": "application/json",
        "x-api-key": api_key,
    }

    body = {
        "model": model,
        "max_tokens": max_tokens,
        "messages": messages,
        "temperature": temperature,
    }
    if system:
        body["system"] = system

    async with httpx.AsyncClient(timeout=120.0) as client:
        resp = await client.post(url, json=body, headers=headers)

    if resp.status_code != 200:
        raise LlmClientError(
            f"LLM API 返回错误 (HTTP {resp.status_code}): {resp.text[:500]}"
        )

    return resp.json()


def extract_text_from_response(data: dict) -> str:
    """从 LLM API 响应中提取文本内容。"""
    content_blocks = data.get("content", [])
    for block in content_blocks:
        if block.get("type") == "text":
            return block.get("text", "")
    return ""
