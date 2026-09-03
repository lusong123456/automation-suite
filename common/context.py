"""ScenarioContext：jsonpath 提取 + {{var}} 模板渲染，用例级独立。"""

from __future__ import annotations

import re
from typing import Any

import jsonpath_ng
from tenacity import retry, stop_after_attempt, wait_fixed

from common.exceptions import ContextExtractionError, RenderError
from common.logging_conf import get_logger

logger = get_logger("context")

# 匹配 {{ var }} 或 {{var}} 形式
_VAR_PATTERN = re.compile(r"\{\{\s*([\w.]+)\s*\}\}")


class ScenarioContext:
    """单用例上下文：set/get/clear + extract + render。

    设计为 function 级 fixture，每个用例独立实例，兼容 xdist 进程模型。
    """

    def __init__(self) -> None:
        self._store: dict[str, Any] = {}

    def set(self, key: str, value: Any) -> None:
        self._store[key] = value

    def get(self, key: str, default: Any = None) -> Any:
        return self._store.get(key, default)

    def clear(self) -> None:
        self._store.clear()

    def all(self) -> dict[str, Any]:
        """返回上下文快照（只读视图）。"""
        return dict(self._store)

    @retry(
        reraise=True,
        stop=stop_after_attempt(1),
        wait=wait_fixed(0),
    )
    def extract(self, response_json: Any, jsonpath_expr: str, alias: str) -> Any:
        """用 jsonpath-ng 从响应中提取值，存入上下文。

        Args:
            response_json: 已解析的响应 JSON。
            jsonpath_expr: 如 "$.id" 或 "$.data.id"。
            alias: 存入上下文的键名。

        Returns:
            提取到的值（首个匹配）。

        Raises:
            ContextExtractionError: 无匹配时抛出。
        """
        try:
            expr = jsonpath_ng.parse(jsonpath_expr)
        except Exception as exc:  # noqa: BLE001
            raise ContextExtractionError(
                f"jsonpath 语法错误：{jsonpath_expr}，原因：{exc}"
            ) from exc

        matches = [m.value for m in expr.find(response_json)]
        if not matches:
            raise ContextExtractionError(
                f"jsonpath 无匹配：{jsonpath_expr}，响应顶层键："
                f"{list(response_json.keys()) if isinstance(response_json, dict) else type(response_json)}"
            )

        value = matches[0]
        self.set(alias, value)
        logger.debug("extract %s -> %s = %r", jsonpath_expr, alias, value)
        return value

    def render(self, template_str: str) -> str:
        """将 {{ var }} 形式的模板用上下文渲染。

        Args:
            template_str: 含 {{ var }} 占位的字符串。

        Returns:
            渲染后的字符串。

        Raises:
            RenderError: 占位变量不存在时抛出。
        """
        if not isinstance(template_str, str):
            return template_str

        def _replace(match: re.Match[str]) -> str:
            key = match.group(1)
            if key not in self._store:
                raise RenderError(
                    f"模板变量未定义：{key}，当前上下文键：{list(self._store.keys())}"
                )
            return str(self._store[key])

        return _VAR_PATTERN.sub(_replace, template_str)

    def __repr__(self) -> str:
        return f"ScenarioContext(keys={list(self._store.keys())})"
