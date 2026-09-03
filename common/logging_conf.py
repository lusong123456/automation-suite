"""日志配置：标准库 logging，INFO 控制台 + DEBUG 文件。"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

_LOG_DIR = Path("reports/logs")
_LOG_FILE = _LOG_DIR / "test.log"
_INITIALIZED = False


def setup_logging() -> None:
    """初始化全局日志配置，幂等可重复调用。"""
    global _INITIALIZED
    if _INITIALIZED:
        return

    _LOG_DIR.mkdir(parents=True, exist_ok=True)

    root = logging.getLogger("automation-suite")
    root.setLevel(logging.DEBUG)
    root.propagate = False

    # 控制台 handler：INFO 级别
    console = logging.StreamHandler(sys.stdout)
    console.setLevel(logging.INFO)
    console.setFormatter(
        logging.Formatter(
            "%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
            datefmt="%H:%M:%S",
        )
    )

    # 文件 handler：DEBUG 级别
    file_handler = logging.FileHandler(_LOG_FILE, encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(
        logging.Formatter(
            "%(asctime)s | %(levelname)-7s | %(name)s:%(lineno)d | %(message)s"
        )
    )

    root.addHandler(console)
    root.addHandler(file_handler)

    # 降低 httpx 等第三方库日志级别
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)

    _INITIALIZED = True


def get_logger(name: str) -> logging.Logger:
    """获取 automation-suite 命名空间下的子 logger。"""
    if not name.startswith("automation-suite"):
        name = f"automation-suite.{name}"
    return logging.getLogger(name)
