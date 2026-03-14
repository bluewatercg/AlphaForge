"""Jinja2 Prompt 模板渲染"""

import logging
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

from config.settings import PROMPTS_DIR

logger = logging.getLogger(__name__)

_env: Environment | None = None


def get_env() -> Environment:
    """获取 Jinja2 环境（单例）"""
    global _env
    if _env is None:
        _env = Environment(
            loader=FileSystemLoader(str(PROMPTS_DIR)),
            autoescape=select_autoescape([]),
            keep_trailing_newline=True,
        )
    return _env


def render_prompt(template_path: str, **variables) -> str:
    """
    渲染 Prompt 模板。

    Args:
        template_path: 相对于 prompts/ 目录的模板路径，如 "macro/sentiment.md"
        **variables: 模板变量

    Returns:
        渲染后的 Prompt 文本
    """
    env = get_env()

    # 读取通用前言
    preamble = ""
    preamble_path = PROMPTS_DIR / "common" / "preamble.md"
    if preamble_path.exists():
        preamble = preamble_path.read_text(encoding="utf-8")

    # 渲染主模板
    template = env.get_template(template_path)
    main_content = template.render(**variables)

    return f"{preamble}\n\n{main_content}"
