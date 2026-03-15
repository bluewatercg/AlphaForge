"""ATLAS-A 入口"""

import argparse
import asyncio
import logging
import os
import sys
from datetime import datetime
from pathlib import Path

# 将项目根目录加入 Python 路径
if getattr(sys, "frozen", False):
    PROJECT_ROOT = Path(sys.executable).parent
else:
    PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv

load_dotenv()

# === 代理处理 ===
# 保存代理配置（LLM API 可能需要），然后清除（AKShare 访问东财不需要）
_SAVED_PROXY = {}
for _key in ("http_proxy", "https_proxy", "HTTP_PROXY", "HTTPS_PROXY",
             "all_proxy", "ALL_PROXY"):
    if _key in os.environ:
        _SAVED_PROXY[_key] = os.environ.pop(_key)

# 将代理信息存入专用变量，供 LLM 客户端使用
if _SAVED_PROXY:
    _proxy_url = _SAVED_PROXY.get("https_proxy") or _SAVED_PROXY.get("http_proxy", "")
    os.environ["_ATLAS_PROXY_URL"] = _proxy_url


def setup_logging(verbose: bool = False):
    """配置日志"""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )
    # 降低第三方库日志级别
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)


def main():
    parser = argparse.ArgumentParser(description="ATLAS-A: A股自我进化选股系统")
    parser.add_argument(
        "--date",
        type=str,
        default=None,
        help="交易日期 YYYYMMDD（默认：最近交易日）",
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="详细日志",
    )
    args = parser.parse_args()

    setup_logging(args.verbose)
    logger = logging.getLogger("atlas-a")

    # 确定日期
    date = args.date
    if date is None:
        date = datetime.now().strftime("%Y%m%d")
        logger.info(f"未指定日期，使用今日: {date}")

    logger.info(f"ATLAS-A v0.1 MVP 启动")
    logger.info(f"目标日期: {date}")

    # 运行流水线
    from src.pipeline.daily_runner import run_daily_pipeline

    result = asyncio.run(run_daily_pipeline(date))

    # 打印报告路径
    report_path = result.get("report_path")
    if report_path:
        print(f"\n📊 日报已生成: {report_path}")
        print(f"\n{'='*60}")
        print(Path(report_path).read_text(encoding="utf-8"))


if __name__ == "__main__":
    main()
