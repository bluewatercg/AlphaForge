"""BaseAgent 抽象基类 + 输出类型定义"""

from __future__ import annotations

import json
import logging
import re
from abc import ABC, abstractmethod
from typing import Any, Optional

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


# === 输出类型 ===


class RegimeOutput(BaseModel):
    """Layer 1 宏观代理输出"""

    agent_id: str
    regime: str = Field(description="RISK_ON / RISK_OFF / NEUTRAL")
    confidence: int = Field(ge=0, le=100)
    reasoning: str
    key_data: dict = Field(default_factory=dict)


class StockPick(BaseModel):
    """单只股票推荐"""

    code: str
    name: str
    action: str = "BUY"
    entry_price: Optional[float] = None
    stop_loss: Optional[float] = None
    target_price: Optional[float] = None
    hold_days: int = 1
    conviction: int = Field(ge=1, le=10, default=5)
    reasoning: str = ""
    catalyst: str = ""


class StockPickOutput(BaseModel):
    """Layer 2 任务代理输出"""

    agent_id: str
    picks: list[StockPick] = Field(default_factory=list)
    market_view: str = ""


class RiskFilterOutput(BaseModel):
    """Layer 3 CRO 风控输出"""

    approved: list[StockPick] = Field(default_factory=list)
    vetoed: list[dict] = Field(default_factory=list)
    risk_level: str = "MEDIUM"
    warnings: list[str] = Field(default_factory=list)


# === 基类 ===


class BaseAgent(ABC):
    """所有代理的抽象基类"""

    def __init__(
        self,
        agent_id: str,
        task: str,
        prompt_path: str,
        weight: float = 1.0,
    ):
        self.agent_id = agent_id
        self.task = task  # "macro" / "A" / "B" / "C" / "D" / "decision"
        self.prompt_path = prompt_path
        self.weight = weight
        self.logger = logging.getLogger(f"agent.{agent_id}")

    @abstractmethod
    async def analyze(self, context: Any) -> BaseModel:
        """执行分析，返回结构化输出"""
        ...

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} id={self.agent_id} weight={self.weight:.2f}>"


def parse_json_from_llm(text: str) -> dict:
    """从 LLM 响应中提取 JSON（处理 markdown code blocks）"""
    # 尝试提取 ```json ... ``` 块
    match = re.search(r"```(?:json)?\s*\n?(.*?)\n?```", text, re.DOTALL)
    if match:
        text = match.group(1)

    # 尝试找到第一个 { 和最后一个 }
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1:
        text = text[start : end + 1]

    try:
        return json.loads(text)
    except json.JSONDecodeError as e:
        logger.error(f"JSON解析失败: {e}\n原始文本: {text[:500]}")
        return {}
