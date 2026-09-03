"""认证相关接口测试。"""

from __future__ import annotations

import allure
import pytest
from pytest_assume.plugin import assume

from common.auth import AuthManager


@allure.epic("API 接口测试")
@allure.feature("认证")
class TestAuth:
    """登录接口测试。"""

    @allure.story("登录成功")
    @pytest.mark.smoke
    def test_login_success(self, suite_config) -> None:
        """验证 POST /api/login 返回 token。"""
        auth = AuthManager(suite_config)

        with allure.step("调用登录接口"):
            token = auth.login()

        with allure.step("验证返回 token 非空"):
            with assume:
                assert token, "token 不应为空"
            with assume:
                assert isinstance(token, str), "token 应为字符串"
            with assume:
                assert len(token) > 10, "token 长度应合理"

    @allure.story("token 复用")
    @pytest.mark.regression
    def test_token_cached(self, auth_manager: AuthManager) -> None:
        """验证 token 在会话内被缓存复用。"""
        with allure.step("第一次获取 token"):
            t1 = auth_manager.token
        with allure.step("第二次获取应命中缓存"):
            t2 = auth_manager.token
        assert t1 == t2, "同一会话内 token 应被缓存复用"
