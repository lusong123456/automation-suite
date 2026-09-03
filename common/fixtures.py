"""全局 pytest fixtures：suite_client、auth_token、api_context。"""

from __future__ import annotations

import pytest

from common.auth import AuthManager
from common.client import SuiteClient
from common.config import get_config
from common.context import ScenarioContext
from common.logging_conf import setup_logging


@pytest.fixture(scope="session", autouse=True)
def _setup_logging() -> None:
    """session 级初始化日志，自动生效。"""
    setup_logging()


@pytest.fixture(scope="session")
def suite_config():  # type: ignore[no-untyped-def]
    """全局配置单例。"""
    return get_config()


@pytest.fixture(scope="session")
def auth_manager(suite_config) -> AuthManager:
    """session 级 AuthManager，登录一次全局复用。"""
    return AuthManager(suite_config)


@pytest.fixture(scope="session")
def auth_token(auth_manager: AuthManager) -> str:
    """session 级 token，自动登录。"""
    return auth_manager.token


@pytest.fixture(scope="session")
def suite_client(suite_config, auth_manager: AuthManager) -> SuiteClient:
    """session 级 SuiteClient，yield 后自动 close。"""
    client = SuiteClient(config=suite_config, auth=auth_manager)
    yield client
    client.close()


@pytest.fixture
def api_context() -> ScenarioContext:
    """function 级 ScenarioContext，每个用例独立实例。"""
    return ScenarioContext()
