"""L0 OpenAPI Spec 完整性守护：8 项静态断言最新一份 spec 自洽。

通过 shared/apijson/api_catalog.py 的 get_default_catalog().list_specs_by_date()
取最新一份 spec（命名 openapi_YYYYMMDD[ _HHMMSS].json）做 8 项检查：
1. JSON 可解析
2. 有 openapi 字段且版本号非空
3. paths 非空 dict
4. 每个 operation 至少有一个 2xx 响应定义
5. 所有 $ref 可解析（递归检查 schemas）
6. required 字段列表无重复
7. path 参数与 path 模板 {var} 一致
8. responses.content 与 schema 配对（jsonschema 校验 schema 自身合法性）

无 spec 时整个文件 skip。jsonschema import 放函数内，缺失时该项跳过。
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import pytest

from shared.apijson.api_catalog import get_default_catalog

# 模块级取最新一份 spec 路径；无 spec 时为 None → 整个文件 skip
_LATEST_SPECS = get_default_catalog().list_specs_by_date()
_LATEST_SPEC: Path | None = _LATEST_SPECS[0] if _LATEST_SPECS else None

pytestmark = pytest.mark.skipif(
    _LATEST_SPEC is None,
    reason="openapi/ 目录下无带日期后缀的 spec，L0 完整性测试跳过",
)


def _load_spec() -> dict[str, Any]:
    """加载最新一份 spec 为 dict。"""
    assert _LATEST_SPEC is not None  # pytestmark 已保证
    with _LATEST_SPEC.open("r", encoding="utf-8") as f:
        return json.load(f)


def _iter_operations(spec: dict[str, Any]):
    """迭代所有 (method, path, operation_dict)。"""
    for path, methods in (spec.get("paths") or {}).items():
        if not isinstance(methods, dict):
            continue
        for method, op in methods.items():
            if method.lower() not in {"get", "post", "put", "delete", "patch"}:
                continue
            yield method.lower(), path, op


def _walk_nodes(node: Any):
    """递归遍历 spec 中所有 dict / list 节点。"""
    if isinstance(node, dict):
        yield node
        for v in node.values():
            yield from _walk_nodes(v)
    elif isinstance(node, list):
        for item in node:
            yield from _walk_nodes(item)


_PATH_PARAM_RE = re.compile(r"\{([^}]+)\}")


@pytest.mark.contract
def test_01_json_parseable() -> None:
    """1. JSON 可解析（json.load 不抛）。"""
    spec = _load_spec()
    assert isinstance(spec, dict), "spec 顶层应为 dict"


@pytest.mark.contract
def test_02_openapi_version() -> None:
    """2. 有 openapi 字段且版本号非空。"""
    spec = _load_spec()
    version = spec.get("openapi")
    assert version, "缺少 openapi 字段或为空"
    assert isinstance(version, str), f"openapi 版本号应为 str，实际 {type(version)}"


@pytest.mark.contract
def test_03_paths_nonempty() -> None:
    """3. paths 非空 dict。"""
    spec = _load_spec()
    paths = spec.get("paths")
    assert isinstance(paths, dict), "paths 应为 dict"
    assert len(paths) > 0, "paths 不应为空"


@pytest.mark.contract
def test_04_operations_have_2xx() -> None:
    """4. 每个 operation 至少有一个 2xx 响应定义。"""
    spec = _load_spec()
    missing: list[str] = []
    for method, path, op in _iter_operations(spec):
        responses = op.get("responses")
        if not isinstance(responses, dict) or not responses:
            missing.append(f"{method.upper()} {path}: 无 responses")
            continue
        has_2xx = any(
            code.startswith("2") or code == "default"
            for code in responses.keys()
        )
        if not has_2xx:
            missing.append(f"{method.upper()} {path}: 无 2xx 响应")
    assert not missing, "存在无 2xx 响应的 operation:\n" + "\n".join(missing)


@pytest.mark.contract
def test_05_refs_resolvable() -> None:
    """5. 所有 $ref 可解析（递归检查 schemas）。"""
    spec = _load_spec()
    # 收集所有可解析的 schema 名（components.schemas.<name>）
    schemas = (spec.get("components") or {}).get("schemas") or {}
    known = {f"#/components/schemas/{k}" for k in schemas.keys()}
    # 也允许 parameters / responses 等 components 子段
    for sub in ("parameters", "responses", "requestBodies"):
        sub_dict = (spec.get("components") or {}).get(sub) or {}
        known |= {f"#/components/{sub}/{k}" for k in sub_dict.keys()}

    unresolved: list[str] = []
    for node in _walk_nodes(spec):
        if not isinstance(node, dict):
            continue
        ref = node.get("$ref")
        if isinstance(ref, str) and ref.startswith("#/"):
            if ref not in known:
                unresolved.append(ref)
    assert not unresolved, "存在无法解析的内部 $ref:\n" + "\n".join(unresolved)


@pytest.mark.contract
def test_06_required_no_duplicates() -> None:
    """6. required 字段列表无重复。"""
    spec = _load_spec()
    dups: list[str] = []
    for node in _walk_nodes(spec):
        if not isinstance(node, dict):
            continue
        req = node.get("required")
        if not isinstance(req, list) or not req:
            continue
        seen: set[str] = set()
        for field in req:
            if field in seen:
                dups.append(f"{node.get('title', '<no-title>')}: 重复 required 字段 {field}")
            seen.add(field)
    assert not dups, "存在 required 字段重复:\n" + "\n".join(dups)


@pytest.mark.contract
def test_07_path_params_consistent() -> None:
    """7. path 参数与 path 模板 {var} 一致。"""
    spec = _load_spec()
    mismatches: list[str] = []
    for path, methods in (spec.get("paths") or {}).items():
        if not isinstance(methods, dict):
            continue
        template_params = set(_PATH_PARAM_RE.findall(path))
        # pathitem 级 parameters（共享给所有 operation）
        shared_params = methods.get("parameters") or []
        shared_param_names = {
            (p.get("name") if isinstance(p, dict) else None)
            for p in shared_params
        }
        # 每个 operation 的 parameters
        for method, op in methods.items():
            if method.lower() not in {"get", "post", "put", "delete", "patch"}:
                continue
            op_params = op.get("parameters") or []
            op_param_names = {
                (p.get("name") if isinstance(p, dict) else None)
                for p in op_params
            }
            all_param_names = shared_param_names | op_param_names
            # 模板里的 {var} 必须有对应 parameter 定义
            missing = template_params - all_param_names
            if missing:
                mismatches.append(
                    f"{method.upper()} {path}: 模板参数 {missing} 无 parameter 定义"
                )
            # 反向：parameter 中类型为 path 的必须在模板里
            for p in op_params + list(shared_params):
                if (
                    isinstance(p, dict)
                    and p.get("in") == "path"
                    and p.get("name") not in template_params
                ):
                    mismatches.append(
                        f"{method.upper()} {path}: parameter {p.get('name')} "
                        f"声明 in=path 但模板中无此变量"
                    )
    assert not mismatches, "path 参数与模板不一致:\n" + "\n".join(mismatches)


@pytest.mark.contract
def test_08_response_content_schema_valid() -> None:
    """8. responses.content 与 schema 配对（jsonschema 校验 schema 自身合法性）。

    jsonschema import 放函数内：缺失时跳过该项（不强制安装）。
    """
    jsonschema = pytest.importorskip("jsonschema")  # 缺失时 skip 本测试

    spec = _load_spec()
    # 解析所有 components.schemas 供 $ref 校验
    schemas = (spec.get("components") or {}).get("schemas") or {}
    issues: list[str] = []
    for method, path, op in _iter_operations(spec):
        responses = op.get("responses") or {}
        for code, resp in responses.items():
            if not isinstance(resp, dict):
                continue
            content = resp.get("content")
            if content is None:
                continue  # 无 body 的响应允许
            if not isinstance(content, dict) or not content:
                issues.append(f"{method.upper()} {path} {code}: content 应为非空 dict")
                continue
            for media_type, media in content.items():
                if not isinstance(media, dict):
                    continue
                schema = media.get("schema")
                if schema is None:
                    issues.append(
                        f"{method.upper()} {path} {code} {media_type}: 缺少 schema"
                    )
                    continue
                # 用 jsonschema 校验 schema 自身合法性（Draft 07）
                try:
                    jsonschema.Draft7Validator.check_schema(schema)
                except jsonschema.SchemaError as exc:
                    issues.append(
                        f"{method.upper()} {path} {code} {media_type}: "
                        f"非法 JSON Schema → {exc.message}"
                    )
    assert not issues, "responses.content 与 schema 配对问题:\n" + "\n".join(issues)
