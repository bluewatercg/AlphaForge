"""MarketContext：汇聚所有市场数据为一个统一上下文对象"""

import logging
from dataclasses import dataclass, field
from datetime import datetime

import pandas as pd

from src.data import (
    fund_flow,
    index_data,
    market_data,
    sector_data,
    sentiment_data,
)

logger = logging.getLogger(__name__)


@dataclass
class MarketContext:
    """一个交易日的完整市场上下文"""

    date: str  # YYYYMMDD

    # 指数数据
    index_summary: dict = field(default_factory=dict)

    # 全市场快照
    all_stocks_spot: pd.DataFrame = field(default_factory=pd.DataFrame)
    tradeable_stocks: pd.DataFrame = field(default_factory=pd.DataFrame)

    # 情绪数据
    sentiment: dict = field(default_factory=dict)
    limit_up_pool: pd.DataFrame = field(default_factory=pd.DataFrame)
    limit_up_previous: pd.DataFrame = field(default_factory=pd.DataFrame)

    # 资金流
    north_flow: pd.DataFrame = field(default_factory=pd.DataFrame)
    fund_flow_rank: pd.DataFrame = field(default_factory=pd.DataFrame)

    # 板块
    industry_boards: pd.DataFrame = field(default_factory=pd.DataFrame)
    concept_boards: pd.DataFrame = field(default_factory=pd.DataFrame)

    # 环境信号（Layer 1 输出后填充）
    regime: str = "NEUTRAL"
    regime_confidence: int = 50
    regime_reasoning: str = ""

    def summary_text(self) -> str:
        """生成简洁的市场概况文本（用于 Prompt 注入）"""
        lines = [f"## 市场概况 ({self.date})"]

        # 指数
        if self.index_summary:
            lines.append("\n### 主要指数")
            for name, info in self.index_summary.items():
                chg = info.get("change_pct", 0)
                price = info.get("latest_price", 0)
                sign = "+" if chg >= 0 else ""
                lines.append(f"- {name}: {price:.2f} ({sign}{chg:.2f}%)")

        # 情绪
        if self.sentiment:
            s = self.sentiment
            lines.append(f"\n### 涨停生态")
            lines.append(f"- 涨停: {s.get('zt_count', 0)}家")
            lines.append(f"- 跌停: {s.get('dt_count', 0)}家")
            lines.append(f"- 炸板: {s.get('zhaban_count', 0)}家 (炸板率{s.get('zhaban_rate', 0)}%)")
            lines.append(f"- 最高连板: {s.get('max_lianban', 0)}板 ({s.get('max_lianban_stock', '')})")
            if s.get("lianban_distribution"):
                dist_str = ", ".join(f"{k}:{v}家" for k, v in s["lianban_distribution"].items())
                lines.append(f"- 连板分布: {dist_str}")

        # 北向资金
        if not self.north_flow.empty:
            try:
                latest = self.north_flow.iloc[-1]
                north_val = latest.get("北向资金", latest.get("当日净流入", 0))
                lines.append(f"\n### 北向资金")
                lines.append(f"- 最新净流入: {north_val}亿")
            except Exception:
                pass

        # 行业板块 Top 5
        if not self.industry_boards.empty:
            lines.append("\n### 行业板块涨幅前5")
            top5 = self.industry_boards.head(5)
            for _, row in top5.iterrows():
                name = row.get("板块名称", "")
                chg = row.get("涨跌幅", 0)
                leader = row.get("领涨股票", "")
                lines.append(f"- {name}: {chg:+.2f}% (领涨: {leader})")

        # 概念板块 Top 5
        if not self.concept_boards.empty:
            lines.append("\n### 概念板块涨幅前5")
            top5 = self.concept_boards.head(5)
            for _, row in top5.iterrows():
                name = row.get("板块名称", "")
                chg = row.get("涨跌幅", 0)
                lines.append(f"- {name}: {chg:+.2f}%")

        # 主力资金 Top 10
        if not self.fund_flow_rank.empty:
            lines.append("\n### 主力资金净流入前10")
            top10 = self.fund_flow_rank.head(10)
            for _, row in top10.iterrows():
                code = row.get("代码", "")
                name = row.get("名称", "")
                flow = row.get("主力净流入-净额", row.get("主力净流入", 0))
                lines.append(f"- {code} {name}: {flow}")

        return "\n".join(lines)

    def top_gainers(self, n: int = 30) -> pd.DataFrame:
        """获取涨幅前N的可交易股票（排除ST/停牌/涨停）"""
        df = self.tradeable_stocks
        if df.empty or "涨跌幅" not in df.columns:
            return pd.DataFrame()
        return df.nlargest(n, "涨跌幅").reset_index(drop=True)


def build_market_context(date: str) -> MarketContext:
    """
    构建完整的市场上下文。

    Args:
        date: 日期 "YYYYMMDD"

    Returns:
        填充完毕的 MarketContext
    """
    logger.info(f"[build_market_context] 开始构建 {date} 市场上下文")

    ctx = MarketContext(date=date)

    # 每个数据源独立容错，单个失败不阻塞整体
    def safe_call(name, fn, *args, default=None):
        try:
            return fn(*args)
        except Exception as e:
            logger.warning(f"  [{name}] 获取失败: {e}")
            return default

    # 1. 指数
    ctx.index_summary = safe_call("指数", index_data.get_index_summary, date, default={})
    logger.info(f"  指数数据: {len(ctx.index_summary)} 个")

    # 2. 全市场快照
    ctx.all_stocks_spot = safe_call("全市场", market_data.get_all_stocks_spot, default=pd.DataFrame())
    if not isinstance(ctx.all_stocks_spot, pd.DataFrame):
        ctx.all_stocks_spot = pd.DataFrame()
    ctx.tradeable_stocks = market_data.filter_tradeable(ctx.all_stocks_spot)
    logger.info(
        f"  全市场: {len(ctx.all_stocks_spot)}只, "
        f"可交易: {len(ctx.tradeable_stocks)}只"
    )

    # 3. 情绪数据
    ctx.sentiment = safe_call("情绪", sentiment_data.get_sentiment_summary, date, default={})
    if not isinstance(ctx.sentiment, dict):
        ctx.sentiment = {}
    ctx.limit_up_pool = safe_call("涨停池", sentiment_data.get_limit_up_pool, date, default=pd.DataFrame())
    if not isinstance(ctx.limit_up_pool, pd.DataFrame):
        ctx.limit_up_pool = pd.DataFrame()
    ctx.limit_up_previous = safe_call("昨涨停", sentiment_data.get_limit_up_previous, date, default=pd.DataFrame())
    if not isinstance(ctx.limit_up_previous, pd.DataFrame):
        ctx.limit_up_previous = pd.DataFrame()
    logger.info(f"  涨停: {ctx.sentiment.get('zt_count', 0)}家")

    # 4. 资金流
    ctx.north_flow = safe_call("北向", fund_flow.get_north_flow, default=pd.DataFrame())
    if not isinstance(ctx.north_flow, pd.DataFrame):
        ctx.north_flow = pd.DataFrame()
    ctx.fund_flow_rank = safe_call("主力资金", fund_flow.get_individual_fund_flow_rank, "今日", default=pd.DataFrame())
    if not isinstance(ctx.fund_flow_rank, pd.DataFrame):
        ctx.fund_flow_rank = pd.DataFrame()
    logger.info(f"  北向数据: {len(ctx.north_flow)}条")

    # 5. 板块
    ctx.industry_boards = safe_call("行业板块", sector_data.get_industry_boards, default=pd.DataFrame())
    if not isinstance(ctx.industry_boards, pd.DataFrame):
        ctx.industry_boards = pd.DataFrame()
    ctx.concept_boards = safe_call("概念板块", sector_data.get_concept_boards, default=pd.DataFrame())
    if not isinstance(ctx.concept_boards, pd.DataFrame):
        ctx.concept_boards = pd.DataFrame()
    logger.info(
        f"  行业板块: {len(ctx.industry_boards)}个, "
        f"概念板块: {len(ctx.concept_boards)}个"
    )

    logger.info(f"[build_market_context] {date} 上下文构建完成")
    return ctx
