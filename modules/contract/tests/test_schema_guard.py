"""L1 契约守护：实际响应必须符合本地 JSON Schema。

被测接口（https://reqres.in）：
- POST /api/users   创建用户 → 必须返回 {id, name, job, createdAt}
- GET  /api/users/{id}  查询用户 → 必须返回 {data: {...}, support: {...}}

设计要点：
- 复用全局 suite_client fixture 发请求（含认证、日志、重试、401 刷新）
- 复用 common.reporting.attach_json 把实际响应贴到 allure
- 用 jsonschema.Draft202012Validator.iter_errors 收集所有违反点，一次性断言
- 与 api 模块的功能测试区分：本测试只校验"形状"，不校验具体值
"""

from __future__ import annotations

import allure
import pytest
from jsonschema import Draft202012Validator

from common.client import SuiteClient
from common.reporting import attach_json
from modules.api.models import UserCreateRequestFactory

# reqres.in 仅 1-12 号用户可查询，超出会 404
_QUERYABLE_USER_IDS = ["1", "2", "3", "4", "5"]


@allure.epic("契约测试")
@allure.feature("L1 Schema 守护")
class TestUserSchemaGuard:
    """用户接口响应结构契约守护。"""

    @allure.story("创建用户响应契约")
    @pytest.mark.contract
    @pytest.mark.smoke
    def test_create_user_schema(
        self,
        suite_client: SuiteClient,
        user_create_schema: dict,
    ) -> None:
        """POST /api/users 响应必须符合 user_create_response.json 契约。"""
        request = UserCreateRequestFactory.build()

        with allure.step("构造随机用户请求"):
            attach_json("请求体", request.model_dump())

        with allure.step("调用创建用户接口"):
            resp = suite_client.post(
                "/api/users",
                json=request.model_dump(),
                with_auth=False,
            )
            resp.raise_for_status()
            body = resp.json()
            attach_json("实际响应", body)

        with allure.step("用本地 schema 校验响应结构"):
            validator = Draft202012Validator(user_create_schema)
            errors = sorted(validator.iter_errors(body), key=lambda e: e.path)
            if errors:
                # 收集所有违反点，一次性失败，避免逐条断言的反复跑
                msg_lines = [
                    f"[{ '.'.join(map(str, e.absolute_path)) or 'root' }] {e.message}"
                    for e in errors
                ]
                attach_json("契约违反点", msg_lines)
                pytest.fail(
                    f"响应不符合 schema 契约，共 {len(errors)} 处违反：\n"
                    + "\n".join(msg_lines)
                )

    @allure.story("查询用户响应契约")
    @pytest.mark.contract
    @pytest.mark.parametrize("user_id", _QUERYABLE_USER_IDS)
    def test_get_user_schema(
        self,
        suite_client: SuiteClient,
        user_get_schema: dict,
        user_id: str,
    ) -> None:
        """GET /api/users/{id} 响应必须符合 user_get_response.json 契约。"""
        with allure.step(f"查询用户 id={user_id}"):
            resp = suite_client.get(f"/api/users/{user_id}", with_auth=False)
            resp.raise_for_status()
            body = resp.json()
            attach_json("实际响应", body)

        with allure.step("用本地 schema 校验响应结构"):
            validator = Draft202012Validator(user_get_schema)
            errors = sorted(validator.iter_errors(body), key=lambda e: e.path)
            if errors:
                msg_lines = [
                    f"[{ '.'.join(map(str, e.absolute_path)) or 'root' }] {e.message}"
                    for e in errors
                ]
                attach_json("契约违反点", msg_lines)
                pytest.fail(
                    f"响应不符合 schema 契约，共 {len(errors)} 处违反：\n"
                    + "\n".join(msg_lines)
                )
