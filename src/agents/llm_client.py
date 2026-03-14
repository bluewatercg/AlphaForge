"""LLM 客户端封装 - 支持 OpenAI 兼容接口和 Anthropic 原生接口"""

import logging
import os

from config.settings import LLM_MAX_TOKENS, LLM_MODEL, LLM_TEMPERATURE

logger = logging.getLogger(__name__)

_client = None
_backend: str = ""  # "openai" or "anthropic"


def _get_env(key: str) -> str | None:
    """获取环境变量，兼容带引号的 key（如 .env 中 "KEY"="value"）"""
    val = os.getenv(key)
    if val:
        return val.strip('"').strip("'")
    # 尝试带引号的 key
    val = os.getenv(f'"{key}"')
    if val:
        return val.strip('"').strip("'")
    return None


def _detect_backend() -> str:
    """根据环境变量自动检测使用哪个后端"""
    if _get_env("OPENAI_API_KEY"):
        return "openai"
    if _get_env("ANTHROPIC_API_KEY"):
        return "anthropic"
    raise RuntimeError(
        "未找到 API Key。请在 .env 中设置 OPENAI_API_KEY（OpenAI兼容接口）"
        "或 ANTHROPIC_API_KEY（Anthropic原生接口）"
    )


def get_client():
    """获取单例 LLM 客户端"""
    global _client, _backend
    if _client is not None:
        return _client

    _backend = _detect_backend()

    if _backend == "openai":
        from openai import OpenAI
        import httpx

        base_url = _get_env("OPENAI_BASE_URL") or _get_env("BASE_URL")
        api_key = _get_env("OPENAI_API_KEY")

        # 如果有代理，通过 httpx 配置（避免 SOCKS 依赖问题）
        proxy_url = os.getenv("_ATLAS_PROXY_URL", "")
        http_client = None
        if proxy_url and not proxy_url.startswith("socks"):
            http_client = httpx.Client(proxy=proxy_url)

        _client = OpenAI(
            api_key=api_key,
            base_url=base_url,
            http_client=http_client,
        )
        logger.info(f"[LLM] 使用 OpenAI 兼容接口, base_url={base_url}")
    else:
        import anthropic

        _client = anthropic.Anthropic(api_key=_get_env("ANTHROPIC_API_KEY"))
        logger.info("[LLM] 使用 Anthropic 原生接口")

    return _client


async def call_llm(
    system_prompt: str,
    user_prompt: str,
    model: str | None = None,
    max_tokens: int = LLM_MAX_TOKENS,
    temperature: float = LLM_TEMPERATURE,
) -> str:
    """
    调用 LLM API。自动适配 OpenAI 兼容 / Anthropic 原生。

    Args:
        system_prompt: 系统提示词
        user_prompt: 用户提示词（包含数据和指令）
        model: 模型ID（None则使用配置默认值）
        max_tokens: 最大输出 token 数
        temperature: 温度

    Returns:
        LLM 响应文本
    """
    client = get_client()
    model = model or _get_env("LLM_MODEL") or LLM_MODEL

    logger.info(
        f"[LLM] backend={_backend} model={model} "
        f"system_len={len(system_prompt)} user_len={len(user_prompt)}"
    )

    if _backend == "openai":
        response = client.chat.completions.create(
            model=model,
            max_tokens=max_tokens,
            temperature=temperature,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        )
        response_text = response.choices[0].message.content
        usage = response.usage
        logger.info(
            f"[LLM] response_len={len(response_text)} "
            f"prompt_tokens={usage.prompt_tokens} "
            f"completion_tokens={usage.completion_tokens}"
        )
    else:
        message = client.messages.create(
            model=model,
            max_tokens=max_tokens,
            temperature=temperature,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}],
        )
        response_text = message.content[0].text
        logger.info(
            f"[LLM] response_len={len(response_text)} "
            f"input_tokens={message.usage.input_tokens} "
            f"output_tokens={message.usage.output_tokens}"
        )

    return response_text
