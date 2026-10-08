"""根目录 conftest：导入 common.fixtures，配置 pytest 全局。

session 级 auth_manager 在本文件暴露（当前被测系统：RuoYi-Cloud-Plus）。
多身份 token / 状态机 / 并发 helper 等 L3 / L4 / L5 专用 fixture 在
modules/api/conftest.py 暴露（基于本文件 auth_manager 之上扩展）。
"""

from __future__ import annotations

import pytest

from common.auth import AuthProvider
from common.fixtures import (  # noqa: F401
    _setup_logging,
    api_context,
    auth_token,
    suite_client,
    suite_config,
)
from shared.auth.ruoyi_auth import RuoYiAuthProvider

# pytest 配置项在 pyproject.toml 的 [tool.pytest.ini_options] 中声明，
# 此处仅负责 fixture 暴露，避免重复声明 markers。


@pytest.fixture(scope="session")
def auth_manager(suite_config) -> AuthProvider:  # type: ignore[no-untyped-def]  # noqa: F811
    """session 级认证提供方：当前被测系统是 RuoYi-Cloud-Plus。

    若要切换其他被测系统，在此 fixture 内替换为对应 AuthProvider 子类即可。
    多身份扩展（get_identity / switch_tenant 等）见 shared.auth.base_provider，
    对应的多身份 fixture 在 modules/api/conftest.py 暴露。
    """
    return RuoYiAuthProvider(suite_config)
