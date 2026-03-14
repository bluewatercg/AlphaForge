"""行业板块、概念板块数据"""

import logging

import akshare as ak
import pandas as pd

from src.data.akshare_client import ak_call

logger = logging.getLogger(__name__)


def get_industry_boards() -> pd.DataFrame:
    """
    获取东财行业板块列表及涨跌数据。

    Returns:
        DataFrame with 排名, 板块名称, 板块代码, 最新价, 涨跌幅, 涨跌额,
        成交量, 成交额, 换手率, 上涨家数, 下跌家数, 领涨股票 等列
    """
    try:
        return ak_call(ak.stock_board_industry_name_em, ttl=1800)
    except Exception as e:
        logger.warning(f"获取行业板块失败: {e}")
        return pd.DataFrame()


def get_concept_boards() -> pd.DataFrame:
    """
    获取东财概念板块列表及涨跌数据。

    Returns:
        DataFrame with 排名, 板块名称, 板块代码, 最新价, 涨跌幅 等列
    """
    try:
        return ak_call(ak.stock_board_concept_name_em, ttl=1800)
    except Exception as e:
        logger.warning(f"获取概念板块失败: {e}")
        return pd.DataFrame()


def get_industry_constituents(board_name: str) -> pd.DataFrame:
    """获取某行业板块的成分股"""
    try:
        return ak_call(
            ak.stock_board_industry_cons_em,
            ttl=86400,
            symbol=board_name,
        )
    except Exception as e:
        logger.warning(f"获取行业板块 {board_name} 成分股失败: {e}")
        return pd.DataFrame()


def get_concept_constituents(board_name: str) -> pd.DataFrame:
    """获取某概念板块的成分股"""
    try:
        return ak_call(
            ak.stock_board_concept_cons_em,
            ttl=86400,
            symbol=board_name,
        )
    except Exception as e:
        logger.warning(f"获取概念板块 {board_name} 成分股失败: {e}")
        return pd.DataFrame()
