"""ATLAS-A 全局配置"""

import sys
from pathlib import Path

# === 项目路径 ===
# PyInstaller 打包后，数据文件在 sys._MEIPASS 中，运行时目录在 exe 旁边
if getattr(sys, "frozen", False):
    _BUNDLE_DIR = Path(sys._MEIPASS)
    _EXE_DIR = Path(sys.executable).parent
    PROJECT_ROOT = _EXE_DIR
    PROMPTS_DIR = _BUNDLE_DIR / "prompts"
    STATE_DIR = _EXE_DIR / "state"
    REPORTS_DIR = _EXE_DIR / "reports"
else:
    PROJECT_ROOT = Path(__file__).parent.parent
    PROMPTS_DIR = PROJECT_ROOT / "prompts"
    STATE_DIR = PROJECT_ROOT / "state"
    REPORTS_DIR = PROJECT_ROOT / "reports"

CACHE_DIR = STATE_DIR / "cache"

# === LLM ===
LLM_MODEL = "gpt-5.4"  # 可通过 .env 中 LLM_MODEL 覆盖
LLM_MAX_TOKENS = 4096
LLM_TEMPERATURE = 0.3

# === 达尔文权重 ===
WEIGHT_MIN = 0.3
WEIGHT_MAX = 2.5
WEIGHT_INIT = 1.0
WEIGHT_BOOST = 1.05   # 前25%每日乘数
WEIGHT_DECAY = 0.95   # 后25%每日乘数

# === 任务分配 ===
TASK_ALLOC_INIT = {"A": 0.25, "B": 0.25, "C": 0.25, "D": 0.25}
TASK_ALLOC_MIN = 0.10
TASK_ALLOC_MAX = 0.40
TASK_ALLOC_STEP = 0.05
TASK_ALLOC_REBALANCE_DAYS = 5

# === 评估窗口 ===
EVAL_WINDOWS = {"d1": 1, "d2": 2, "d5": 5, "d10": 10}

# === Autoresearch ===
AUTORESEARCH_TRIGGER_DAYS = 10
AUTORESEARCH_TEST_DAYS = 5
AUTORESEARCH_MIN_RECS = 5  # 最少推荐数才触发

# === AKShare ===
AKSHARE_RATE_LIMIT = 5        # 每秒最大请求数
AKSHARE_RETRY_COUNT = 3
AKSHARE_RETRY_DELAY = 2.0     # 秒

# === A股规则 ===
MAIN_BOARD_LIMIT = 0.10       # 主板涨跌停10%
GEM_BOARD_LIMIT = 0.20        # 创业板/科创板涨跌停20%
ST_LIMIT = 0.05               # ST股涨跌停5%
MAX_POSITION_SINGLE = 0.20    # 单只最大仓位20%
MAX_POSITION_GEM = 0.40       # 创业板/科创板总仓位上限40%

# === MVP 选股数量 ===
TASK_A_PICK_COUNT = 5
