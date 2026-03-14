"""指数数据"""

import logging

import akshare as ak
import pandas as pd

from src.data.akshare_client import ak_call

logger = logging.getLogger(__name__)

# 常用指数代码
INDEXES = {
    "上证指数": "000001",
    "深证成指": "399001",
    "创业板指": "399006",
    "科创50": "000688",
    "沪深300": "000300",
    "中证500": "000905",
    "中证1000": "000852",
}


def get_index_spot() -> pd.DataFrame:
    """获取主要指数实时行情"""
    try:
        return ak_call(ak.stock_zh_index_spot_em, ttl=300)
    except Exception as e:
        logger.warning(f"获取指数行情失败: {e}")
        return pd.DataFrame()


def get_index_daily(
    symbol: str, start_date: str, end_date: str
) -> pd.DataFrame:
    """获取指数日线历史数据"""
    try:
        return ak_call(
            ak.stock_zh_index_daily_em,
            ttl=86400,
            use_disk_cache=True,
            symbol=symbol,
            start_date=start_date,
            end_date=end_date,
        )
    except Exception as e:
        logger.warning(f"获取指数 {symbol} 日线失败: {e}")
        return pd.DataFrame()


def get_index_summary(date: str) -> dict:
    """
    汇总当日主要指数表现。

    Returns:
        dict: {指数名: {latest_price, change_pct, volume}}
    """
    spot = get_index_spot()
    if spot.empty:
        return {}

    result = {}
    for name, code in INDEXES.items():
        row = spot[spot["代码"] == code]
        if row.empty:
            continue
        row = row.iloc[0]
        result[name] = {
            "latest_price": row.get("最新价", 0),
            "change_pct": row.get("涨跌幅", 0),
            "volume": row.get("成交量", 0),
            "amount": row.get("成交额", 0),
        }

    return result
