"""api 模块级 conftest，可放置模块内专用 fixture。"""

from __future__ import annotations

import pytest

from modules.api.services.user_service import UserService


@pytest.fixture
def user_service(suite_client, api_context):  # type: ignore[no-untyped-def]
    """function 级 UserService，注入 suite_client 与 api_context。"""
    return UserService(client=suite_client, context=api_context)
