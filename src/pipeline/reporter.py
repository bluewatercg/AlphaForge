"""每日报告生成器"""

import logging
from datetime import datetime
from pathlib import Path

from src.agents.base_agent import RegimeOutput, RiskFilterOutput, StockPickOutput
from src.data.market_context import MarketContext
from config.settings import REPORTS_DIR

logger = logging.getLogger(__name__)


def generate_daily_report(
    date: str,
    context: MarketContext,
    regime: RegimeOutput,
    picks: StockPickOutput,
    filtered: RiskFilterOutput,
) -> Path:
    """
    生成 Markdown 格式的每日选股报告。

    Returns:
        报告文件路径
    """
    lines = []

    # 标题
    formatted_date = f"{date[:4]}-{date[4:6]}-{date[6:]}"
    lines.append(f"# ATLAS-A 每日选股报告")
    lines.append(f"**日期**: {formatted_date}")
    lines.append(f"**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append("")

    # === 市场环境 ===
    lines.append("---")
    lines.append("## 一、市场环境")
    lines.append("")

    regime_emoji = {"RISK_ON": "🟢", "RISK_OFF": "🔴", "NEUTRAL": "🟡"}
    emoji = regime_emoji.get(regime.regime, "⚪")
    lines.append(f"**环境信号**: {emoji} **{regime.regime}** (置信度: {regime.confidence}/100)")
    lines.append(f"**判断理由**: {regime.reasoning}")
    lines.append("")

    if regime.key_data:
        lines.append("| 指标 | 数值 |")
        lines.append("|------|------|")
        for k, v in regime.key_data.items():
            lines.append(f"| {k} | {v} |")
        lines.append("")

    # 指数表现
    if context.index_summary:
        lines.append("### 主要指数")
        lines.append("| 指数 | 最新价 | 涨跌幅 |")
        lines.append("|------|--------|--------|")
        for name, info in context.index_summary.items():
            price = info.get("latest_price", 0)
            chg = info.get("change_pct", 0)
            sign = "+" if chg >= 0 else ""
            lines.append(f"| {name} | {price:.2f} | {sign}{chg:.2f}% |")
        lines.append("")

    # 涨停生态
    s = context.sentiment
    if s:
        lines.append("### 涨停生态")
        lines.append(f"- 涨停: **{s.get('zt_count', 0)}**家")
        lines.append(f"- 跌停: **{s.get('dt_count', 0)}**家")
        lines.append(f"- 炸板: {s.get('zhaban_count', 0)}家 (炸板率: {s.get('zhaban_rate', 0)}%)")
        lines.append(f"- 最高连板: **{s.get('max_lianban', 0)}板** ({s.get('max_lianban_stock', '')})")
        if s.get("lianban_distribution"):
            dist = ", ".join(f"{k}:{v}家" for k, v in s["lianban_distribution"].items())
            lines.append(f"- 连板分布: {dist}")
        lines.append("")

    # === 选股推荐 ===
    lines.append("---")
    lines.append("## 二、选股推荐")
    lines.append("")
    lines.append(f"**代理**: {picks.agent_id}")
    lines.append(f"**市场观点**: {picks.market_view}")
    lines.append("")

    if filtered.approved:
        lines.append("### 通过风控的推荐")
        lines.append("")
        lines.append("| # | 代码 | 名称 | 买入价 | 止损 | 目标 | 信心 | 理由 | 催化剂 |")
        lines.append("|---|------|------|--------|------|------|------|------|--------|")
        for i, p in enumerate(filtered.approved, 1):
            entry = f"{p.entry_price:.2f}" if p.entry_price else "-"
            sl = f"{p.stop_loss:.2f}" if p.stop_loss else "-"
            tp = f"{p.target_price:.2f}" if p.target_price else "-"
            lines.append(
                f"| {i} | {p.code} | {p.name} | {entry} | {sl} | {tp} | "
                f"{p.conviction}/10 | {p.reasoning} | {p.catalyst} |"
            )
        lines.append("")

    # 被否决的
    if filtered.vetoed:
        lines.append("### 风控否决")
        lines.append("")
        for v in filtered.vetoed:
            lines.append(f"- ~~{v['code']} {v['name']}~~ — {v['reason']}")
        lines.append("")

    # 风控摘要
    lines.append(f"**风险等级**: {filtered.risk_level}")
    if filtered.warnings:
        lines.append("")
        lines.append("**风控提醒**:")
        for w in filtered.warnings:
            lines.append(f"- ⚠️ {w}")
    lines.append("")

    # === 板块热点 ===
    lines.append("---")
    lines.append("## 三、板块热点")
    lines.append("")

    if not context.industry_boards.empty:
        lines.append("### 行业板块 Top 10")
        lines.append("| 排名 | 板块 | 涨跌幅 | 领涨股 |")
        lines.append("|------|------|--------|--------|")
        for i, (_, row) in enumerate(context.industry_boards.head(10).iterrows(), 1):
            name = row.get("板块名称", "")
            chg = row.get("涨跌幅", 0)
            leader = row.get("领涨股票", "")
            lines.append(f"| {i} | {name} | {chg:+.2f}% | {leader} |")
        lines.append("")

    if not context.concept_boards.empty:
        lines.append("### 概念板块 Top 10")
        lines.append("| 排名 | 板块 | 涨跌幅 |")
        lines.append("|------|------|--------|")
        for i, (_, row) in enumerate(context.concept_boards.head(10).iterrows(), 1):
            name = row.get("板块名称", "")
            chg = row.get("涨跌幅", 0)
            lines.append(f"| {i} | {name} | {chg:+.2f}% |")
        lines.append("")

    # === 底部 ===
    lines.append("---")
    lines.append("*ATLAS-A v0.1 MVP | 仅供研究参考，不构成投资建议*")

    # 写入文件
    report_content = "\n".join(lines)
    report_dir = REPORTS_DIR / "daily"
    report_dir.mkdir(parents=True, exist_ok=True)
    report_path = report_dir / f"{formatted_date}.md"
    report_path.write_text(report_content, encoding="utf-8")

    return report_path
