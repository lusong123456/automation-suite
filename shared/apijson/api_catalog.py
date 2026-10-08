"""接口信息查询统一入口：ApiCatalog。

基于两个静态目录工作（路径示例：shared/apijson/）：
- openapi/  ：整份 OpenAPI 文档，命名规则：
    * 默认单份：openapi.json
    * 多份历史：openapi_YYYYMMDD.json 或 openapi_YYYYMMDD_HHMMSS.json
- schemas/ ：按业务域拆开的 JSON Schema（<domain>/<interface>.json）

ApiCatalog 提供：
- get_openapi_spec() / get_schema() / list_endpoints() / get_endpoint()
  ：读"默认"那份 spec（openapi.json，或按日期最新一份）的常用入口
- list_specs_by_date() / get_latest_two_specs()
  ：扫描历史 spec，供 L0 spec 完整性 / diff 守护使用

不在此处做远程拉取或 MCP 获取——文档由人工落地，保证可重复、可审计。
"""

from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path
from typing import Any

_THIS_DIR = Path(__file__).resolve().parent
_OPENAPI_DIR = _THIS_DIR / "openapi"
_SCHEMAS_DIR = _THIS_DIR / "schemas"

# spec 文件名规则：openapi_YYYYMMDD.json 或 openapi_YYYYMMDD_HHMMSS.json
_SPEC_NAME_RE = re.compile(
    r"^openapi_(?P<date>\d{8})(?:_(?P<time>\d{6}))?\.json$"
)


class ApiCatalog:
    """接口信息查询统一入口。

    一个实例对应一组 (openapi/, schemas/) 静态目录。默认指向本包内目录，
    测试中也可传入自定义根（如临时 spec 目录）。
    """

    def __init__(
        self,
        openapi_dir: Path | None = None,
        schemas_dir: Path | None = None,
    ) -> None:
        self.openapi_dir: Path = openapi_dir or _OPENAPI_DIR
        self.schemas_dir: Path = schemas_dir or _SCHEMAS_DIR

    # ------------------------------------------------------------------
    # 单份 spec 入口（默认 openapi.json，否则取最新一份）
    # ------------------------------------------------------------------

    def _resolve_default_spec_path(self) -> Path | None:
        """返回默认 spec 路径：优先 openapi.json，否则取最新一份历史 spec。

        都没有时返回 None。
        """
        direct = self.openapi_dir / "openapi.json"
        if direct.exists():
            return direct
        specs = self.list_specs_by_date()
        return specs[0] if specs else None

    def get_openapi_spec(self) -> dict[str, Any]:
        """加载默认 OpenAPI 文档为 dict。

        无 spec 时抛 FileNotFoundError。
        """
        path = self._resolve_default_spec_path()
        if path is None:
            raise FileNotFoundError(
                f"openapi/ 目录下无 spec：{self.openapi_dir}"
            )
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)

    def get_schema(self, name: str) -> dict[str, Any]:
        """按相对路径名读取 schemas/ 下的 JSON Schema。

        name 形如 "user/login_response.json" 或 "user\\login_response.json"。
        无文件时抛 FileNotFoundError。
        """
        # 兼容 Windows 反斜杠
        rel = Path(*name.replace("\\", "/").split("/"))
        path = self.schemas_dir / rel
        if not path.exists():
            raise FileNotFoundError(f"schema 不存在：{path}")
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)

    def list_endpoints(self) -> list[str]:
        """列出默认 spec 中所有 endpoint（method + path）。

        返回形如 ["GET /users", "POST /users/login"] 的列表。
        无 spec 时返回空列表。
        """
        try:
            spec = self.get_openapi_spec()
        except FileNotFoundError:
            return []
        out: list[str] = []
        for path, methods in (spec.get("paths") or {}).items():
            if not isinstance(methods, dict):
                continue
            for method in methods:
                # 只认标准 HTTP 方法，过滤掉 parameters / $ref 等键
                if method.lower() in {"get", "post", "put", "delete", "patch"}:
                    out.append(f"{method.upper()} {path}")
        return out

    def get_endpoint(self, method: str, path: str) -> dict[str, Any]:
        """取默认 spec 中指定 method+path 的 operation 对象。

        无 spec 或 endpoint 不存在时抛 KeyError。
        """
        spec = self.get_openapi_spec()
        paths = spec.get("paths") or {}
        operation = (paths.get(path) or {}).get(method.lower())
        if operation is None:
            raise KeyError(f"endpoint 不存在：{method.upper()} {path}")
        return operation

    # ------------------------------------------------------------------
    # 多份 spec 入口（L0 完整性 / diff 守护用）
    # ------------------------------------------------------------------

    def list_specs_by_date(self) -> list[Path]:
        """扫描 openapi/ 目录，按文件名日期**降序**返回 spec 文件列表。

        命名规则：
        - openapi_YYYYMMDD.json
        - openapi_YYYYMMDD_HHMMSS.json

        用正则提取日期+时间排序。openapi.json（无日期后缀）不计入此列表。
        无 spec 返回空列表。
        """
        if not self.openapi_dir.exists():
            return []
        items: list[tuple[str, str, Path]] = []
        for entry in self.openapi_dir.iterdir():
            if not entry.is_file():
                continue
            m = _SPEC_NAME_RE.match(entry.name)
            if not m:
                continue
            date = m.group("date")
            time = m.group("time") or "000000"
            items.append((date, time, entry))
        # 降序：日期大、时间大的在前
        items.sort(key=lambda x: (x[0], x[1]), reverse=True)
        return [p for _, _, p in items]

    def get_latest_two_specs(self) -> tuple[dict[str, Any], dict[str, Any]]:
        """返回最新两份 spec（解析为 dict）。

        返回 (最新, 次新)。不足两份抛 ValueError。
        """
        specs = self.list_specs_by_date()
        if len(specs) < 2:
            raise ValueError("openapi/ 目录下 spec 不足两份，无法 diff")
        with specs[0].open("r", encoding="utf-8") as f:
            latest = json.load(f)
        with specs[1].open("r", encoding="utf-8") as f:
            prev = json.load(f)
        return latest, prev


@lru_cache(maxsize=1)
def get_default_catalog() -> ApiCatalog:
    """默认 ApiCatalog 单例：指向 shared/apijson/ 内置目录。"""
    return ApiCatalog()
