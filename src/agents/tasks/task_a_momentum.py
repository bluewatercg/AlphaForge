"""游资动量选股代理 - Layer 2, Task A"""

import logging

from src.agents.base_agent import (
    BaseAgent,
    StockPick,
    StockPickOutput,
    parse_json_from_llm,
)
from src.agents.llm_client import call_llm
from src.agents.prompt_renderer import render_prompt
from src.data.market_context import MarketContext

logger = logging.getLogger(__name__)


class TaskAMomentumAgent(BaseAgent):
    """游资风格动量选股，选5只T+1短线标的"""

    def __init__(self, weight: float = 1.0):
        super().__init__(
            agent_id="task_a_momentum",
            task="A",
            prompt_path="tasks/task_a_momentum.md",
            weight=weight,
        )

    async def analyze(self, context: MarketContext) -> StockPickOutput:
        self.logger.info("开始游资动量选股分析...")

        variables = self._prepare_variables(context)
        user_prompt = render_prompt(self.prompt_path, **variables)

        system_prompt = (
            "你是一位经验丰富的A股短线游资操盘手。"
            "请根据今日市场数据选出最具T+1短线机会的股票。"
            "严格按要求的JSON格式输出，只输出JSON，不要输出其他内容。"
        )
        response = await call_llm(system_prompt, user_prompt)

        return self._parse_response(response)

    def _prepare_variables(self, ctx: MarketContext) -> dict:
        # 市场概况
        market_summary = ctx.summary_text()

        # 涨幅前30可交易
        top_gainers_text = "暂无数据"
        top_df = ctx.top_gainers(30)
        if not top_df.empty:
            rows = []
            cols = ["代码", "名称", "最新价", "涨跌幅", "成交量", "成交额", "换手率"]
            available_cols = [c for c in cols if c in top_df.columns]
            for _, row in top_df.iterrows():
                parts = [f"{c}:{row[c]}" for c in available_cols]
                rows.append(" | ".join(parts))
            top_gainers_text = "\n".join(rows)

        # 涨停池详情
        limit_up_text = "暂无数据"
        if not ctx.limit_up_pool.empty:
            rows = []
            for _, row in ctx.limit_up_pool.head(20).iterrows():
                code = row.get("代码", "")
                name = row.get("名称", "")
                lianban = row.get("连板数", 1)
                first_time = row.get("首次封板时间", "")
                zhaban = row.get("炸板次数", 0)
                industry = row.get("所属行业", "")
                rows.append(
                    f"- {code} {name} | {lianban}连板 | "
                    f"首封:{first_time} | 炸板:{zhaban}次 | {industry}"
                )
            limit_up_text = "\n".join(rows)

        # 昨日涨停今日表现
        yesterday_zt_text = "暂无数据"
        if not ctx.limit_up_previous.empty:
            rows = []
            for _, row in ctx.limit_up_previous.head(15).iterrows():
                code = row.get("代码", "")
                name = row.get("名称", "")
                chg = row.get("涨跌幅", 0)
                rows.append(f"- {code} {name}: {chg:+.2f}%")
            yesterday_zt_text = "\n".join(rows)

        return {
            "current_date": ctx.date,
            "regime": ctx.regime,
            "regime_confidence": ctx.regime_confidence,
            "regime_reasoning": ctx.regime_reasoning,
            "market_summary": market_summary,
            "top_gainers": top_gainers_text,
            "limit_up_detail": limit_up_text,
            "yesterday_zt_detail": yesterday_zt_text,
        }

    def _parse_response(self, response: str) -> StockPickOutput:
        data = parse_json_from_llm(response)

        if not data:
            self.logger.warning("LLM 返回无法解析的JSON，返回空推荐")
            return StockPickOutput(agent_id=self.agent_id, picks=[], market_view="解析失败")

        picks = []
        for p in data.get("picks", []):
            try:
                pick = StockPick(
                    code=str(p.get("code", "")).zfill(6),
                    name=p.get("name", ""),
                    action=p.get("action", "BUY"),
                    entry_price=p.get("entry_price"),
                    stop_loss=p.get("stop_loss"),
                    target_price=p.get("target_price"),
                    hold_days=p.get("hold_days", 1),
                    conviction=min(max(p.get("conviction", 5), 1), 10),
                    reasoning=p.get("reasoning", ""),
                    catalyst=p.get("catalyst", ""),
                )
                picks.append(pick)
            except Exception as e:
                self.logger.warning(f"解析单只股票推荐失败: {e}, raw={p}")

        return StockPickOutput(
            agent_id=self.agent_id,
            picks=picks,
            market_view=data.get("market_view", ""),
        )
