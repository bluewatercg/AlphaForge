"""MVP 每日流水线：情绪代理 → 动量选股 → CRO过滤 → 日报"""

import asyncio
import logging
from datetime import datetime

from src.agents.base_agent import RiskFilterOutput, RegimeOutput, StockPickOutput
from src.agents.decision.cro_filter import cro_filter
from src.agents.macro.sentiment_agent import SentimentAgent
from src.agents.tasks.task_a_momentum import TaskAMomentumAgent
from src.data.market_context import MarketContext, build_market_context
from src.pipeline.reporter import generate_daily_report

logger = logging.getLogger(__name__)


async def run_daily_pipeline(date: str) -> dict:
    """
    运行 MVP 每日流水线。

    Args:
        date: 交易日期 "YYYYMMDD"

    Returns:
        dict with keys: context, regime, picks, filtered, report_path
    """
    logger.info(f"{'='*60}")
    logger.info(f"ATLAS-A MVP 每日流水线 - {date}")
    logger.info(f"{'='*60}")

    # === Phase 1: 数据采集 ===
    logger.info("[Phase 1] 构建市场上下文...")
    ctx = build_market_context(date)

    # === Phase 2: Layer 1 - 情绪代理 ===
    logger.info("[Phase 2] 运行情绪分析代理...")
    sentiment_agent = SentimentAgent()
    regime_output: RegimeOutput = await sentiment_agent.analyze(ctx)

    # 将环境信号写入上下文
    ctx.regime = regime_output.regime
    ctx.regime_confidence = regime_output.confidence
    ctx.regime_reasoning = regime_output.reasoning

    logger.info(
        f"  环境信号: {regime_output.regime} "
        f"(置信度: {regime_output.confidence})"
    )

    # === Phase 3: Layer 2 - 动量选股代理 ===
    logger.info("[Phase 3] 运行动量选股代理...")
    momentum_agent = TaskAMomentumAgent()
    picks_output: StockPickOutput = await momentum_agent.analyze(ctx)

    logger.info(f"  推荐 {len(picks_output.picks)} 只股票")
    for p in picks_output.picks:
        logger.info(f"    {p.code} {p.name} 信心={p.conviction} {p.reasoning}")

    # === Phase 4: Layer 3 - CRO 风控 ===
    logger.info("[Phase 4] 运行CRO风控过滤...")
    filtered: RiskFilterOutput = cro_filter(picks_output, ctx)

    logger.info(f"  通过: {len(filtered.approved)}, 否决: {len(filtered.vetoed)}")
    for v in filtered.vetoed:
        logger.info(f"    [否决] {v['code']} {v['name']}: {v['reason']}")

    # === Phase 5: 生成日报 ===
    logger.info("[Phase 5] 生成每日报告...")
    report_path = generate_daily_report(
        date=date,
        context=ctx,
        regime=regime_output,
        picks=picks_output,
        filtered=filtered,
    )
    logger.info(f"  报告已保存: {report_path}")

    logger.info(f"{'='*60}")
    logger.info(f"流水线完成!")
    logger.info(f"{'='*60}")

    return {
        "context": ctx,
        "regime": regime_output,
        "picks": picks_output,
        "filtered": filtered,
        "report_path": report_path,
    }
