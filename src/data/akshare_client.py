"""AKShare 统一封装：重试、限速、缓存、代理绕过"""

import os
import time
import hashlib
import logging
from pathlib import Path
from typing import Any, Callable
from unittest.mock import patch

import requests
import pandas as pd

from config.settings import (
    AKSHARE_RATE_LIMIT,
    AKSHARE_RETRY_COUNT,
    AKSHARE_RETRY_DELAY,
    CACHE_DIR,
)

logger = logging.getLogger(__name__)

# 内存缓存：{cache_key: (timestamp, dataframe)}
_memory_cache: dict[str, tuple[float, pd.DataFrame]] = {}

# 限速：上次请求时间戳列表
_request_timestamps: list[float] = []

# === 强制 AKShare 请求不走代理 ===
# Monkey-patch requests.Session 让所有 AKShare 的 HTTP 请求跳过代理
_original_session_init = requests.Session.__init__


def _patched_session_init(self, *args, **kwargs):
    _original_session_init(self, *args, **kwargs)
    # 强制不走代理
    self.trust_env = False
    self.proxies = {"http": None, "https": None}


requests.Session.__init__ = _patched_session_init
logger.debug("[akshare_client] 已 patch requests.Session 跳过代理")


def _rate_limit():
    """确保每秒不超过 AKSHARE_RATE_LIMIT 次请求"""
    now = time.time()
    # 清理1秒前的记录
    while _request_timestamps and _request_timestamps[0] < now - 1.0:
        _request_timestamps.pop(0)
    if len(_request_timestamps) >= AKSHARE_RATE_LIMIT:
        sleep_time = 1.0 - (now - _request_timestamps[0])
        if sleep_time > 0:
            time.sleep(sleep_time)
    _request_timestamps.append(time.time())


def _cache_key(func_name: str, kwargs: dict) -> str:
    """生成缓存key"""
    raw = f"{func_name}:{sorted(kwargs.items())}"
    return hashlib.md5(raw.encode()).hexdigest()


def ak_call(
    func: Callable,
    ttl: int = 3600,
    use_disk_cache: bool = False,
    **kwargs: Any,
) -> pd.DataFrame:
    """
    调用 AKShare 函数，带重试、限速、缓存。

    Args:
        func: AKShare 函数
        ttl: 内存缓存过期时间（秒），默认1小时
        use_disk_cache: 是否启用磁盘缓存（用于历史数据）
        **kwargs: 传给 AKShare 函数的参数
    """
    func_name = func.__name__
    key = _cache_key(func_name, kwargs)

    # 1. 检查内存缓存
    if key in _memory_cache:
        cached_time, cached_df = _memory_cache[key]
        if time.time() - cached_time < ttl:
            logger.debug(f"[cache hit] {func_name}({kwargs})")
            return cached_df.copy()

    # 2. 检查磁盘缓存
    if use_disk_cache:
        disk_path = CACHE_DIR / f"{key}.parquet"
        if disk_path.exists():
            age = time.time() - disk_path.stat().st_mtime
            if age < ttl:
                logger.debug(f"[disk cache hit] {func_name}({kwargs})")
                df = pd.read_parquet(disk_path)
                _memory_cache[key] = (time.time(), df)
                return df.copy()

    # 3. 调用 AKShare（带重试和限速）
    last_error = None
    for attempt in range(1, AKSHARE_RETRY_COUNT + 1):
        try:
            _rate_limit()
            logger.info(f"[ak_call] {func_name}({kwargs}) attempt={attempt}")
            df = func(**kwargs)
            if df is None:
                df = pd.DataFrame()
            break
        except Exception as e:
            last_error = e
            logger.warning(f"[ak_call] {func_name} attempt {attempt} failed: {e}")
            if attempt < AKSHARE_RETRY_COUNT:
                time.sleep(AKSHARE_RETRY_DELAY * attempt)
    else:
        logger.error(f"[ak_call] {func_name} all {AKSHARE_RETRY_COUNT} attempts failed")
        raise RuntimeError(
            f"AKShare call {func_name}({kwargs}) failed after {AKSHARE_RETRY_COUNT} retries"
        ) from last_error

    # 4. 写入缓存
    _memory_cache[key] = (time.time(), df)
    if use_disk_cache:
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        try:
            df.to_parquet(CACHE_DIR / f"{key}.parquet", index=False)
        except Exception as e:
            logger.warning(f"[disk cache write failed] {e}")

    return df.copy()


def clear_cache():
    """清除所有内存缓存"""
    _memory_cache.clear()
