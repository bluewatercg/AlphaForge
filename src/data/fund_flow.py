"""资金流向数据：北向资金、主力资金"""

import logging

import akshare as ak
import pandas as pd

from src.data.akshare_client import ak_call

logger = logging.getLogger(__name__)


def get_north_flow() -> pd.DataFrame:
    """
    获取北向资金（沪股通+深股通）净流入数据。

    Returns:
        DataFrame with 日期, 沪股通, 深股通, 北向资金 等列
    """
    try:
        return ak_call(
            ak.stock_hsgt_north_net_flow_in_em,
            ttl=3600,
            indicator="北上",
        )
    except Exception as e:
        logger.warning(f"获取北向资金失败: {e}")
        return pd.DataFrame()


def get_individual_fund_flow_rank(indicator: str = "今日") -> pd.DataFrame:
    """
    获取个股资金流排名。

    Args:
        indicator: "今日" / "3日" / "5日" / "10日"

    Returns:
        DataFrame with 代码, 名称, 最新价, 主力净流入, 超大单净流入 等列
    """
    try:
        return ak_call(
            ak.stock_individual_fund_flow_rank,
            ttl=1800,
            indicator=indicator,
        )
    except Exception as e:
        logger.warning(f"获取个股资金流排名失败: {e}")
        return pd.DataFrame()


def get_market_fund_flow() -> pd.DataFrame:
    """获取大盘资金流向"""
    try:
        return ak_call(ak.stock_market_fund_flow, ttl=3600)
    except Exception as e:
        logger.warning(f"获取大盘资金流向失败: {e}")
        return pd.DataFrame()
