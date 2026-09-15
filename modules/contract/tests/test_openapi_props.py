"""L2 OpenAPI 属性测试骨架：schemathesis 自动生成请求并校验响应。

启用前置条件：
1. 被测服务必须暴露 OpenAPI 文档（如 {BASE_URL}/openapi.json 或 /swagger.json）
2. 安装 L2 依赖：pip install -e ".[contract]"，其中 contract 包含 schemathesis
3. 取消下方 SCHEMA 的注释与 skip 标记

reqres.in 没有完整 OpenAPI 文档，因此默认 skip。
当你的被测服务有 OpenAPI 时，将 BASE_URL 指向该服务并放开 skip。

工作原理（schemathesis）：
- 读取 OpenAPI 文档，知道每个接口的请求格式与响应格式
- 自动给每个接口生成几十到几百个合法请求去发
- 每个返回都拿去和 OpenAPI 中声明的 schema 对比
- 自动发现"我没写到的边界"与"违反 spec 的响应"
"""

from __future__ import annotations

import pytest

# 当被测服务提供 OpenAPI 文档时，放开下面三行注释并删除 skip
# import schemathesis
# from common.config import get_config
# from common.auth import AuthManager
#
# _config = get_config()
# _auth = AuthManager(_config)
#
# SCHEMA = schemathesis.openapi.from_url(
#     f"{_config.BASE_URL}/openapi.json",
#     headers={"Authorization": f"Bearer {_auth.token}"},
# )


_ALLURE_SKIP_REASON = "reqres.in 无 OpenAPI 文档，L2 属性测试需被测服务提供 OpenAPI"


@pytest.mark.contract
@pytest.mark.skip(reason=_ALLURE_SKIP_REASON)
def test_openapi_contract_placeholder() -> None:
    """L2 占位：被测服务有 OpenAPI 文档后改为下方写法。

    写法（取消文件顶部的注释后）：

        @pytest.mark.contract
        @SCHEMA.parametrize()
        def test_openapi_contract(case):
            \"\"\"schemathesis 自动给每个接口生成请求。\"\"\"
            response = case.call()
            case.validate_response(response)

    case.validate_response 会校验：
    - 状态码是否符合 OpenAPI 声明
    - 响应 headers / body 是否符合 schema
    - 不符合时给出违反点的可读描述
    """
    pytest.skip(_ALLURE_SKIP_REASON)
