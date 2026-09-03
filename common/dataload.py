"""yaml 数据加载器：加载 data/ 下的边界测试数据。"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from common.logging_conf import get_logger

logger = get_logger("dataload")

_DATA_DIR = Path("data")


def load_yaml(path: str | Path) -> list[dict[str, Any]]:
    """加载 yaml 文件，返回参数列表（用于 pytest.mark.parametrize）。

    Args:
        path: 相对 data/ 的路径，或绝对路径。

    Returns:
        list[dict]：yaml 中 top-level 列表的每一项。

    Raises:
        FileNotFoundError: 文件不存在。
        yaml.YAMLError: 解析失败。
    """
    p = Path(path)
    if not p.is_absolute():
        p = _DATA_DIR / p
    if not p.exists():
        raise FileNotFoundError(f"数据文件不存在：{p}")

    with p.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    if isinstance(data, dict):
        # 支持单一字典形式
        return [data]
    if isinstance(data, list):
        return data
    raise ValueError(f"yaml 文件 {p} 顶层应为 list 或 dict，实际为 {type(data)}")
