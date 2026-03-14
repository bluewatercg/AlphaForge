"""市场情绪代理 - Layer 1"""

import json
import logging

from src.agents.base_agent import BaseAgent, RegimeOutput, parse_json_from_llm
from src.agents.llm_client import call_llm
from src.agents.prompt_renderer import render_prompt
from src.data.market_context import MarketContext

logger = logging.getLogger(__name__)


class SentimentAgent(BaseAgent):
    """分析涨停生态、资金流向、指数表现，输出市场环境信号"""

    def __init__(self, weight: float = 1.0):
        super().__init__(
            agent_id="macro_sentiment",
            task="macro",
            prompt_path="macro/sentiment.md",
            weight=weight,
        )

    async def analyze(self, context: MarketContext) -> RegimeOutput:
        self.logger.info("开始分析市场情绪...")

        # 准备模板变量
        variables = self._prepare_variables(context)

        # 渲染 Prompt
        user_prompt = render_prompt(self.prompt_path, **variables)

        # 调用 LLM
        system_prompt = (
            "你是一位经验丰富的A股市场情绪分析师。"
            "请根据提供的数据严格按要求的JSON格式输出分析结果。"
            "只输出JSON，不要输出其他内容。"
        )
        response = await call_llm(system_prompt, user_prompt)

        # 解析输出
        return self._parse_response(response)

    def _prepare_variables(self, ctx: MarketContext) -> dict:
        # 指数概况
        index_lines = []
        for name, info in ctx.index_summary.items():
            chg = info.get("change_pct", 0)
            price = info.get("latest_price", 0)
            index_lines.append(f"- {name}: {price:.2f} ({chg:+.2f}%)")
        index_summary = "\n".join(index_lines) if index_lines else "暂无数据"

        # 昨日涨停今日表现
        yesterday_zt = "暂无数据"
        if not ctx.limit_up_previous.empty:
            rows = []
            for _, row in ctx.limit_up_previous.head(10).iterrows():
                code = row.get("代码", "")
                name = row.get("名称", "")
                chg = row.get("涨跌幅", 0)
                rows.append(f"- {code} {name}: {chg:+.2f}%")
            yesterday_zt = "\n".join(rows)

        # 北向资金
        north_summary = "暂无数据"
        if not ctx.north_flow.empty:
            try:
                latest = ctx.north_flow.tail(3)
                rows = []
                for _, row in latest.iterrows():
                    date_val = row.get("日期", row.get("date", ""))
                    flow = row.get("当日净流入", row.get("北向资金", 0))
                    rows.append(f"- {date_val}: {flow}亿")
                north_summary = "\n".join(rows)
            except Exception:
                pass

        # 行业板块 Top 10
        top_industries = "暂无数据"
        if not ctx.industry_boards.empty:
            rows = []
            for _, row in ctx.industry_boards.head(10).iterrows():
                name = row.get("板块名称", "")
                chg = row.get("涨跌幅", 0)
                leader = row.get("领涨股票", "")
                rows.append(f"- {name}: {chg:+.2f}% (领涨: {leader})")
            top_industries = "\n".join(rows)

        # 概念板块 Top 10
        top_concepts = "暂无数据"
        if not ctx.concept_boards.empty:
            rows = []
            for _, row in ctx.concept_boards.head(10).iterrows():
                name = row.get("板块名称", "")
                chg = row.get("涨跌幅", 0)
                rows.append(f"- {name}: {chg:+.2f}%")
            top_concepts = "\n".join(rows)

        # 主力资金 Top 10
        fund_flow_top10 = "暂无数据"
        if not ctx.fund_flow_rank.empty:
            rows = []
            for _, row in ctx.fund_flow_rank.head(10).iterrows():
                code = row.get("代码", "")
                name = row.get("名称", "")
                flow = row.get("主力净流入-净额", row.get("主力净流入", 0))
                rows.append(f"- {code} {name}: {flow}")
            fund_flow_top10 = "\n".join(rows)

        return {
            "current_date": ctx.date,
            "index_summary": index_summary,
            "sentiment": ctx.sentiment,
            "yesterday_zt_performance": yesterday_zt,
            "north_flow_summary": north_summary,
            "top_industries": top_industries,
            "top_concepts": top_concepts,
            "fund_flow_top10": fund_flow_top10,
        }

    def _parse_response(self, response: str) -> RegimeOutput:
        data = parse_json_from_llm(response)

        if not data:
            self.logger.warning("LLM 返回无法解析的JSON，使用默认 NEUTRAL")
            return RegimeOutput(
                agent_id=self.agent_id,
                regime="NEUTRAL",
                confidence=30,
                reasoning="LLM响应解析失败，默认观望",
            )

        return RegimeOutput(
            agent_id=self.agent_id,
            regime=data.get("regime", "NEUTRAL"),
            confidence=data.get("confidence", 50),
            reasoning=data.get("reasoning", ""),
            key_data=data.get("key_data", {}),
        )
