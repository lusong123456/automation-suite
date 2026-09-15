"""契约加载器：本地 schema 文件、远程 OpenAPI 文档、pydantic 模型转 schema。

三种契约来源：
1. 本地 JSON Schema 文件（modules/contract/schemas/*.json）—— L1 守护用
2. 被测服务的 OpenAPI 文档（{BASE_URL}/openapi.json）—— L2 属性测试用
3. api 模块的 pydantic 模型转 JSON Schema —— 避免双写
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

import httpx

from common.config import SuiteConfig, get_config
from common.exceptions import ContractError
from common.logging_conf import get_logger

logger = get_logger("contract.loaders")

# schemas 目录：当前文件所在目录下的 schemas/
SCHEMA_DIR = Path(__file__).parent / "schemas"


def load_schema(filename: str) -> dict[str, Any]:
    """加载本地 JSON Schema 文件。

    Args:
        filename: schemas 目录下的文件名，如 "user_create_response.json"。

    Returns:
        解析后的 schema 字典。

    Raises:
        ContractError: 文件不存在或 JSON 解析失败。
    """
    path = SCHEMA_DIR / filename
    if not path.exists():
        raise ContractError(f"Schema 文件不存在：{path}")
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ContractError(f"Schema JSON 解析失败：{path}，原因：{exc}") from exc


@lru_cache(maxsize=1)
def load_openapi_spec(
    endpoint: str = "/openapi.json",
    config: SuiteConfig | None = None,
) -> dict[str, Any]:
    """从被测服务拉取 OpenAPI 文档（缓存）。

    Args:
        endpoint: OpenAPI 文档路径，默认 /openapi.json。
        config: 配置对象，默认用全局单例。

    Returns:
        OpenAPI 文档字典。

    Raises:
        ContractError: 拉取失败或状态码非 2xx。
    """
    cfg = config or get_config()
    url = f"{cfg.BASE_URL}{endpoint}"
    logger.info("拉取 OpenAPI 文档：%s", url)
    try:
        resp = httpx.get(url, timeout=10)
        resp.raise_for_status()
    except httpx.HTTPError as exc:
        raise ContractError(f"OpenAPI 文档拉取失败：{url}，原因：{exc}") from exc
    return resp.json()


def schema_from_pydantic(model_cls: type) -> dict[str, Any]:
    """从 pydantic v2 模型生成 JSON Schema，避免 schema 与模型双写。

    Args:
        model_cls: pydantic BaseModel 子类。

    Returns:
        JSON Schema 字典。
    """
    try:
        return model_cls.model_json_schema()
    except Exception as exc:  # noqa: BLE001
        raise ContractError(f"pydantic 模型转 schema 失败：{model_cls}，原因：{exc}") from exc
