"""L0 OpenAPI Spec 差异守护：对比最新两份 spec，仅破坏性变化 fail。

通过 shared/apijson/api_catalog.py 的 get_default_catalog().get_latest_two_specs()
取最新两份 spec，用 deepdiff.DeepDiff 比对：

破坏性变化（fail）：
- 删除字段（dictionary_item_removed）
- 类型变更（type_changes）
- required 收紧（旧 required ⊊ 新 required，新增必填字段）

兼容性变化（warn，打 log + allure attach）：
- 新增字段（dictionary_item_added）
- 新增 endpoint（paths 下新增 path）
- 新增可选响应 / content 类型

deepdiff import 放函数内，缺失时 skip。
不足两份 spec 时 skip。
"""

from __future__ import annotations

import logging
from typing import Any

import pytest

from shared.apijson.api_catalog import get_default_catalog

logger = logging.getLogger("contract.spec_diff")

# 不足两份时整个文件 skip
try:
    _LATEST, _PREV = get_default_catalog().get_latest_two_specs()
    _SPECS_AVAILABLE = True
except (ValueError, FileNotFoundError):
    _SPECS_AVAILABLE = False

pytestmark = pytest.mark.skipif(
    not _SPECS_AVAILABLE,
    reason="openapi/ 目录下 spec 不足两份，L0 diff 跳过",
)


def _collect_required(spec: dict[str, Any]) -> dict[str, list[str]]:
    """收集所有 components.schemas.<name>.required。"""
    out: dict[str, list[str]] = {}
    schemas = (spec.get("components") or {}).get("schemas") or {}
    for name, schema in schemas.items():
        if isinstance(schema, dict):
            req = schema.get("required") or []
            if isinstance(req, list):
                out[name] = list(req)
    return out


def _find_required_tightening(
    prev: dict[str, Any], latest: dict[str, Any]
) -> list[str]:
    """检测 required 收紧：旧 required ⊊ 新 required。

    返回收紧 schema 的描述列表（schema 名 + 新增的 required 字段）。
    """
    prev_req = _collect_required(prev)
    latest_req = _collect_required(latest)
    tightening: list[str] = []
    for name, latest_fields in latest_req.items():
        prev_fields = set(prev_req.get(name, []))
        latest_fields_set = set(latest_fields)
        # 收紧：旧字段全部保留 + 新增字段
        if prev_fields <= latest_fields_set and (latest_fields_set - prev_fields):
            added = sorted(latest_fields_set - prev_fields)
            tightening.append(
                f"schema {name}: required 收紧，新增必填 {added}"
            )
    return tightening


@pytest.mark.contract
def test_no_breaking_changes_between_latest_two() -> None:
    """最新两份 spec 间不允许出现破坏性变化（删除 / 类型变更 / required 收紧）。"""
    deepdiff = pytest.importorskip("deepdiff")  # 缺失时 skip
    from deepdiff import DeepDiff

    assert _SPECS_AVAILABLE  # pytestmark 已保证

    diff: dict[str, Any] = DeepDiff(_PREV, _LATEST, ignore_order=True)

    breaking: list[str] = []

    # 1. 删除字段
    removed = diff.get("dictionary_item_removed") or []
    if removed:
        breaking.append("删除字段:\n" + "\n".join(f"  - {r}" for r in removed))

    # 2. 类型变更
    type_changes = diff.get("type_changes") or []
    if type_changes:
        breaking.append(
            "类型变更:\n"
            + "\n".join(f"  - {tc}" for tc in type_changes)
        )

    # 3. required 收紧
    tightening = _find_required_tightening(_PREV, _LATEST)
    if tightening:
        breaking.append("required 收紧:\n" + "\n".join(f"  - {t}" for t in tightening))

    # 兼容性变化：仅 warn
    compatible: list[str] = []
    added = diff.get("dictionary_item_added") or []
    if added:
        compatible.append("新增字段/endpoint:\n" + "\n".join(f"  + {a}" for a in added))

    # 输出报告（allure 优先，否则 print）
    report_lines = ["=== OpenAPI Spec Diff Report ==="]
    if breaking:
        report_lines.append("\n--- 破坏性变化（fail）---")
        report_lines.extend(breaking)
    if compatible:
        report_lines.append("\n--- 兼容性变化（warn）---")
        report_lines.extend(compatible)
    if not breaking and not compatible:
        report_lines.append("无显著差异")
    report = "\n".join(report_lines)

    try:
        import allure

        allure.attach(report, name="spec_diff_report", attachment_type=allure.attachment_type.TEXT)
    except ImportError:
        print(report)

    if compatible:
        logger.warning("兼容性变化（warn）:\n%s", "\n".join(compatible))

    assert not breaking, "检测到破坏性变化（删除字段 / 类型变更 / required 收紧）:\n" + "\n".join(breaking)
