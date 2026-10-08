"""L2 OpenAPI 属性测试骨架：schemathesis 自动生成请求并校验响应。

启用前置条件：
1. 本地存在带日期后缀的 OpenAPI 文档（如 shared/apijson/openapi/openapi_YYYYMMDD.json，
   由人工维护）。_SPEC_PATH 自动取 list_specs_by_date() 最新一份。
2. 安装 L2 依赖：pip install -e ".[contract]"，其中 contract 包含 schemathesis。
3. 取消下方 SCHEMA 的注释与 skip 标记。

工作原理（schemathesis）：
- 读取 OpenAPI 文档，知道每个接口的请求格式与响应格式
- 自动给每个接口生成几十到几百个合法请求去发
- 每个返回都拿去和 OpenAPI 中声明的 schema 对比
- 自动发现"没写到的边界"与"违反 spec 的响应"

注意：schemathesis 发请求前需通过全局 auth_manager（根 conftest）拿 Bearer token
并注入到每个请求。若被测系统需要额外鉴权头（如 clientid），在 case.headers 中一并补齐。
"""

from __future__ import annotations

from pathlib import Path

import pytest

from shared.apijson.api_catalog import get_default_catalog

# OpenAPI spec 路径：取 list_specs_by_date() 最新一份（无 spec 时为 None → 整个文件 skip）
_SPECS = get_default_catalog().list_specs_by_date()
_SPEC_PATH: Path | None = _SPECS[0] if _SPECS else None

pytestmark = pytest.mark.skipif(
    _SPEC_PATH is None,
    reason="openapi/ 目录下无带日期后缀的 spec，L2 属性测试跳过",
)

# 当 L2 正式启用时，放开下面注释并删除 test_openapi_contract_placeholder 的 skip：
#
# import schemathesis
#
# SCHEMA = schemathesis.openapi.from_path(str(_SPEC_PATH))
#
#
# @SCHEMA.parametrize()
# def test_openapi_contract(case, auth_manager) -> None:
#     """schemathesis 自动给每个接口生成请求。"""
#     # 注入鉴权头（Bearer token；如需 clientid 等额外头在此补齐）
#     case.headers = case.headers or {}
#     case.headers["Authorization"] = f"Bearer {auth_manager.token}"
#     response = case.call()
#     case.validate_response(response)


_SKIP_REASON = "L2 属性测试尚未启用：确认 spec 与鉴权注入后放开 SCHEMA 参数化"


@pytest.mark.contract
@pytest.mark.skip(reason=_SKIP_REASON)
def test_openapi_contract_placeholder() -> None:
    """L2 占位：spec 就位、鉴权注入确认后按文件头部注释改写为参数化用例。"""
    pytest.skip(_SKIP_REASON)
