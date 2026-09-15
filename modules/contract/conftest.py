"""contract 模块级 conftest：暴露契约测试专用 fixture。

复用全局 suite_client（来自 common.fixtures）发请求，
本 conftest 只负责契约侧的 schema 加载等专属 fixture。
"""

from __future__ import annotations

import pytest

from modules.contract.loaders import load_schema


@pytest.fixture
def user_create_schema() -> dict:
    """加载用户创建响应的本地 JSON Schema。"""
    return load_schema("user_create_response.json")


@pytest.fixture
def user_get_schema() -> dict:
    """加载用户查询响应的本地 JSON Schema。"""
    return load_schema("user_get_response.json")
