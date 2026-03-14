"""CRO 风控过滤代理 - Layer 3（硬规则，不调LLM）"""

import logging
import re

from src.agents.base_agent import RiskFilterOutput, StockPick, StockPickOutput
from src.data.market_context import MarketContext

logger = logging.getLogger(__name__)


def cro_filter(
    picks_output: StockPickOutput,
    context: MarketContext,
) -> RiskFilterOutput:
    """
    硬规则风控过滤。不调用 LLM，纯规则判断。

    过滤规则：
    1. ST股
    2. 停牌股（成交量=0）
    3. 已涨停股（涨幅≥9.8%主板 / ≥19.8%创业板）
    4. 代码格式校验
    """
    approved = []
    vetoed = []
    warnings = []

    # 构建全市场快照的查找表
    spot_map: dict[str, dict] = {}
    if not context.all_stocks_spot.empty:
        for _, row in context.all_stocks_spot.iterrows():
            code = str(row.get("代码", "")).strip()
            if code:
                spot_map[code] = row.to_dict()

    for pick in picks_output.picks:
        code = pick.code.strip()
        name = pick.name

        # 规则1：代码格式
        if not re.match(r"^\d{6}$", code):
            vetoed.append({"code": code, "name": name, "reason": f"代码格式无效: {code}"})
            continue

        # 规则2：ST股
        if "ST" in name.upper():
            vetoed.append({"code": code, "name": name, "reason": "ST股"})
            continue

        # 查找市场数据
        spot = spot_map.get(code, {})

        if spot:
            spot_name = str(spot.get("名称", ""))
            # 再次检查名称是否ST
            if "ST" in spot_name.upper():
                vetoed.append({"code": code, "name": name, "reason": f"ST股({spot_name})"})
                continue

            # 规则3：停牌
            volume = spot.get("成交量", 0)
            if volume == 0:
                vetoed.append({"code": code, "name": name, "reason": "停牌（成交量为0）"})
                continue

            # 规则4：涨停（买不到）
            change_pct = spot.get("涨跌幅", 0)
            is_gem = code.startswith("3") or code.startswith("68")  # 创业板/科创板
            limit = 19.8 if is_gem else 9.8
            if change_pct >= limit:
                vetoed.append({
                    "code": code,
                    "name": name,
                    "reason": f"已涨停({change_pct:+.2f}%)，买不到",
                })
                continue
        else:
            warnings.append(f"{code} {name}: 未在全市场快照中找到，无法验证")

        approved.append(pick)

    # 整体风险评估
    risk_level = "LOW"
    if context.regime == "RISK_OFF":
        risk_level = "HIGH"
        warnings.append("市场环境为RISK_OFF，建议降低仓位")
    elif context.regime == "NEUTRAL":
        risk_level = "MEDIUM"

    logger.info(
        f"[CRO] 审核完成: 通过{len(approved)}, 否决{len(vetoed)}, "
        f"风险等级={risk_level}"
    )

    return RiskFilterOutput(
        approved=approved,
        vetoed=vetoed,
        risk_level=risk_level,
        warnings=warnings,
    )
