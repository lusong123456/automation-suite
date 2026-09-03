"""用户接口测试：单接口契约 + 多步骤场景。

被测接口：https://reqres.in
- POST /api/users   创建用户
- GET  /api/users/{id}  查询用户
"""

from __future__ import annotations

import allure
import pytest
from pytest_assume.plugin import assume

from modules.api.models import UserCreateRequest, UserCreateRequestFactory, UserCreateResponse
from modules.api.services import UserService


@allure.epic("API 接口测试")
@allure.feature("用户管理")
class TestUserCreate:
    """用户创建接口契约 + 功能测试。"""

    @allure.story("单接口契约")
    @pytest.mark.smoke
    def test_create_user_contract(self, user_service: UserService) -> None:
        """验证 POST /api/users 响应结构与关键字段。"""
        with allure.step("构造随机用户请求"):
            request = UserCreateRequestFactory.build()
            allure.attach(
                request.model_dump_json(),
                name="请求体",
                attachment_type=allure.attachment_type.JSON,
            )

        with allure.step("调用创建用户接口"):
            resp = user_service.create_user(request)

        with allure.step("验证响应契约"):
            with assume:
                assert resp.id, "id 不应为空"
            with assume:
                assert resp.name == request.name, f"name 应为 {request.name}"
            with assume:
                assert resp.job == request.job, f"job 应为 {request.job}"
            with assume:
                assert resp.createdAt, "createdAt 不应为空"

    @allure.story("单接口契约 - 边界")
    @pytest.mark.regression
    @pytest.mark.parametrize(
        "name,job,should_pass",
        [
            ("普通用户", "工程师", True),
            ("", "工程师", False),  # 空名应被 pydantic 拦截
            ("用户", "", False),   # 空 job 应被拦截
        ],
    )
    def test_create_user_validation(
        self,
        name: str,
        job: str,
        should_pass: bool,
    ) -> None:
        """验证 UserCreateRequest 的 validator 行为。"""
        if should_pass:
            req = UserCreateRequest(name=name, job=job)
            assert req.name == name
            assert req.job == job
        else:
            with pytest.raises(Exception):  # noqa: PT011, BLE001
                UserCreateRequest(name=name, job=job)


@allure.epic("API 接口测试")
@allure.feature("用户管理")
class TestUserScenario:
    """多步骤场景测试：创建 → 查询。"""

    @allure.story("多步骤场景")
    @pytest.mark.e2e
    def test_create_then_query(self, user_service: UserService) -> None:
        """Step1 创建用户提取 id → Step2 查询用户使用 {{ user_id }} 模板。"""
        with allure.step("Step1: 创建用户并提取 user_id"):
            request = UserCreateRequestFactory.build()
            created: UserCreateResponse = user_service.create_user(request)
            allure.attach(
                created.model_dump_json(),
                name="创建响应",
                attachment_type=allure.attachment_type.JSON,
            )
            assert created.id, "创建响应应包含 id"

        with allure.step("Step2: 用 {{ user_id }} 模板渲染查询用户"):
            # get_user 默认从 context 渲染 {{ user_id }}
            # reqres 的 /api/users/{id} 对真实创建的 id 可能返回 404，
            # 这里用 1-12 的固定 id 验证查询链路（reqres 限制）
            user_data = user_service.get_user(user_id="2")

        with allure.step("验证查询结果结构"):
            with assume:
                assert "data" in user_data, "响应应包含 data 字段"
            with assume:
                assert user_data["data"]["id"] == 2, "查询 id 应为 2"
            with assume:
                assert "email" in user_data["data"], "data 应包含 email"
