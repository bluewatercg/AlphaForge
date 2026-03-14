"""个股行情数据"""

import logging
from datetime import datetime

import akshare as ak
import pandas as pd

from src.data.akshare_client import ak_call

logger = logging.getLogger(__name__)


def get_stock_daily(symbol: str, start_date: str, end_date: str) -> pd.DataFrame:
    """
    获取个股日线数据。

    Args:
        symbol: 股票代码，如 "000001"
        start_date: 开始日期 "YYYYMMDD"
        end_date: 结束日期 "YYYYMMDD"

    Returns:
        DataFrame with columns: 日期,开盘,收盘,最高,最低,成交量,成交额,振幅,涨跌幅,涨跌额,换手率
    """
    return ak_call(
        ak.stock_zh_a_hist,
        ttl=86400,
        use_disk_cache=True,
        symbol=symbol,
        period="daily",
        start_date=start_date,
        end_date=end_date,
        adjust="qfq",
    )


def get_all_stocks_spot() -> pd.DataFrame:
    """
    获取A股全市场实时/最近行情快照。

    Returns:
        DataFrame，每行一只股票，包含代码、名称、最新价、涨跌幅、成交量、成交额等。
    """
    return ak_call(ak.stock_zh_a_spot_em, ttl=300)


def get_stock_info(symbol: str) -> pd.DataFrame:
    """获取个股基本信息"""
    return ak_call(
        ak.stock_individual_info_em,
        ttl=86400,
        symbol=symbol,
    )


def filter_tradeable(df: pd.DataFrame) -> pd.DataFrame:
    """
    从全市场快照中过滤可交易股票：
    - 排除ST
    - 排除停牌（成交量为0或最新价为0）
    - 排除涨停（买不到）
    """
    if df.empty:
        return df

    filtered = df.copy()

    # 排除ST
    if "名称" in filtered.columns:
        filtered = filtered[~filtered["名称"].str.contains("ST", na=False)]

    # 排除停牌（成交量或成交额为0）
    if "成交量" in filtered.columns:
        filtered = filtered[filtered["成交量"] > 0]

    # 排除涨停（涨幅接近10%或20%的，买不到）
    if "涨跌幅" in filtered.columns:
        filtered = filtered[filtered["涨跌幅"] < 9.8]

    return filtered.reset_index(drop=True)
