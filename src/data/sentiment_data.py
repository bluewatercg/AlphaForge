"""市场情绪数据：涨停池、跌停池、炸板池、连板数据"""

import logging

import akshare as ak
import pandas as pd

from src.data.akshare_client import ak_call

logger = logging.getLogger(__name__)


def get_limit_up_pool(date: str) -> pd.DataFrame:
    """
    获取涨停股池。

    Args:
        date: 日期 "YYYYMMDD"

    Returns:
        DataFrame with 代码, 名称, 涨停价, 最新价, 成交额, 流通市值, 封板资金,
        首次封板时间, 最后封板时间, 炸板次数, 涨停统计, 连板数, 所属行业
    """
    try:
        return ak_call(ak.stock_zt_pool_em, ttl=3600, date=date)
    except Exception as e:
        logger.warning(f"获取涨停池失败 {date}: {e}")
        return pd.DataFrame()


def get_limit_up_previous(date: str) -> pd.DataFrame:
    """获取昨日涨停股今日表现"""
    try:
        return ak_call(ak.stock_zt_pool_previous_em, ttl=3600, date=date)
    except Exception as e:
        logger.warning(f"获取昨日涨停今日表现失败: {e}")
        return pd.DataFrame()


def get_limit_down_pool(date: str) -> pd.DataFrame:
    """获取跌停股池"""
    try:
        return ak_call(ak.stock_zt_pool_dtgc_em, ttl=3600, date=date)
    except Exception as e:
        logger.warning(f"获取跌停池失败: {e}")
        return pd.DataFrame()


def get_broken_limit_pool(date: str) -> pd.DataFrame:
    """获取炸板池（曾触及涨停但未封住）"""
    try:
        return ak_call(ak.stock_zt_pool_zbgc_em, ttl=3600, date=date)
    except Exception as e:
        logger.warning(f"获取炸板池失败: {e}")
        return pd.DataFrame()


def get_strong_stock_pool(date: str) -> pd.DataFrame:
    """获取强势股池"""
    try:
        return ak_call(ak.stock_zt_pool_strong_em, ttl=3600, date=date)
    except Exception as e:
        logger.warning(f"获取强势股池失败: {e}")
        return pd.DataFrame()


def get_sentiment_summary(date: str) -> dict:
    """
    汇总情绪指标。

    Returns:
        dict with keys: zt_count, dt_count, zhaban_count, max_lianban, etc.
    """
    zt = get_limit_up_pool(date)
    dt = get_limit_down_pool(date)
    zhaban = get_broken_limit_pool(date)

    zt_count = len(zt) if not zt.empty else 0
    dt_count = len(dt) if not dt.empty else 0
    zhaban_count = len(zhaban) if not zhaban.empty else 0

    # 最高连板数
    max_lianban = 0
    max_lianban_stock = ""
    if not zt.empty and "连板数" in zt.columns:
        max_idx = zt["连板数"].idxmax()
        max_lianban = int(zt.loc[max_idx, "连板数"])
        max_lianban_stock = zt.loc[max_idx, "名称"] if "名称" in zt.columns else ""

    # 炸板率
    zhaban_rate = 0.0
    total_touch = zt_count + zhaban_count
    if total_touch > 0:
        zhaban_rate = round(zhaban_count / total_touch * 100, 1)

    # 连板分布
    lianban_dist = {}
    if not zt.empty and "连板数" in zt.columns:
        lianban_dist = zt["连板数"].value_counts().sort_index().to_dict()
        lianban_dist = {f"{int(k)}板": int(v) for k, v in lianban_dist.items()}

    return {
        "zt_count": zt_count,
        "dt_count": dt_count,
        "zhaban_count": zhaban_count,
        "zhaban_rate": zhaban_rate,
        "max_lianban": max_lianban,
        "max_lianban_stock": max_lianban_stock,
        "lianban_distribution": lianban_dist,
    }
