"""contract 模块级 conftest：暴露契约测试专用 fixture。

复用全局 suite_client（来自 common.fixtures）发请求，
本 conftest 暴露契约侧专属 fixture（schema 加载、链路资源等）。
"""

from __future__ import annotations

# 契约测试专用 fixture 按项目/业务域在此追加：
# - L1 spec 完整性 / diff 守护：直接读 openapi.json，无需 fixture
# - L2 schemathesis：见 tests/test_openapi_props.py
# - 写副作用链路：见 tests/links/，yield fixture 链尾自清理
