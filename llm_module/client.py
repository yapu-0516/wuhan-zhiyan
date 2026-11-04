"""最小可用的 DeepSeek 调用封装。"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from openai import APIConnectionError, APIStatusError, AuthenticationError, OpenAI, RateLimitError
from pydantic import BaseModel, Field

ENV_FILE = Path(__file__).with_name(".env")


class LLMError(RuntimeError):
    """对外暴露的安全错误，不包含请求头或 API Key。"""


class Settings(BaseModel):
    api_key: str = Field(min_length=1)
    base_url: str = "https://api.deepseek.com"
    model: str = "deepseek-chat"
    timeout_seconds: float = Field(default=60, gt=0)

    @classmethod
    def from_env(cls) -> "Settings":
        load_dotenv(ENV_FILE)
        api_key = os.getenv("DEEPSEEK_API_KEY", "").strip()
        if not api_key:
            raise LLMError(f"未配置 DEEPSEEK_API_KEY，请填写 {ENV_FILE}")
        return cls(
            api_key=api_key,
            base_url=os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com").strip(),
            model=os.getenv("DEEPSEEK_MODEL", "deepseek-chat").strip(),
            timeout_seconds=float(os.getenv("DEEPSEEK_TIMEOUT_SECONDS", "60")),
        )


def _client(settings: Settings) -> OpenAI:
    return OpenAI(
        api_key=settings.api_key,
        base_url=settings.base_url,
        timeout=settings.timeout_seconds,
    )


def ask(
    prompt: str,
    *,
    system_prompt: str | None = None,
    settings: Settings | None = None,
    client: Any | None = None,
    temperature: float = 0.2,
    max_tokens: int = 1024,
    response_format: dict[str, str] | None = None,
) -> str:
    """发送一轮对话并返回文本；错误统一转换为 LLMError。"""
    prompt = prompt.strip()
    if not prompt:
        raise LLMError("问题不能为空")

    active_settings = settings or Settings.from_env()
    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})

    try:
        kwargs = {
            "model": active_settings.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if response_format:
            kwargs["response_format"] = response_format
        response = (client or _client(active_settings)).chat.completions.create(
            **kwargs
        )
    except AuthenticationError as exc:
        raise LLMError("API Key 无效或没有访问权限") from exc
    except RateLimitError as exc:
        raise LLMError("请求过于频繁或额度不足，请稍后重试") from exc
    except APIConnectionError as exc:
        raise LLMError("无法连接大模型服务，请检查网络或接口地址") from exc
    except APIStatusError as exc:
        raise LLMError(f"大模型服务返回错误，HTTP {exc.status_code}") from exc

    content = response.choices[0].message.content
    if not content:
        raise LLMError("大模型返回了空内容")
    return content
