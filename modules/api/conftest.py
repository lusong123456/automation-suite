"""api 模块级 conftest：暴露 L3 / L4 / L5 三层测试所需的 fixture 骨架。

复用根 conftest 的 session 级 auth_manager（common.auth.AuthProvider 实例），
本 conftest 在其之上暴露多身份 token、状态机模板、并发 helper 的 fixture 占位。

【约束】本文件是**框架骨架**：fixture 体用注释占位，不写空实现。
等具体被测系统落地多身份 Provider（继承 shared.auth.base_provider.AuthProvider，
实现 get_identity / switch_tenant / clear_tenant）后，按注释指引放开实现。
"""

from __future__ import annotations

import pytest

# ---------------------------------------------------------------------------
# 多身份 token fixture（L3 权限隔离用）
# ---------------------------------------------------------------------------
#
# 前置：根 conftest 的 auth_manager 需升级为多身份 Provider
#       （继承 shared.auth.base_provider.AuthProvider，
#        实现 get_identity(identity)）。
# identity 取值约定：super / tenant_a / tenant_b / anonymous。
#
# 当前 RuoYiAuthProvider 仅实现 common.auth.AuthProvider（单身份），
# 因此以下 fixture 体留作注释占位，避免运行时调用未实现的方法。
# 等具体项目落地多身份 Provider 后，按下方注释放开 return。

# @pytest.fixture(scope="session")
# def super_token(auth_manager) -> str:
#     """超管身份 token。"""
#     return auth_manager.get_identity("super")
#
#
# @pytest.fixture(scope="session")
# def tenant_a_token(auth_manager) -> str:
#     """租户 A 身份 token。"""
#     return auth_manager.get_identity("tenant_a")
#
#
# @pytest.fixture(scope="session")
# def tenant_b_token(auth_manager) -> str:
#     """租户 B 身份 token。"""
#     return auth_manager.get_identity("tenant_b")
#
#
# @pytest.fixture(scope="session")
# def anonymous_token() -> str:
#     """匿名身份 token（通常为空字符串或占位）。"""
#     # 匿名请求一般不带 Authorization 头，此处返回空串占位
#     return ""


# ---------------------------------------------------------------------------
# 状态机 fixture 模板（L4 业务流转用）
# ---------------------------------------------------------------------------
#
# 业务流转测试需要在多接口间共享状态（如创建后拿 ID 再查询/更新/删除）。
# 用 yield fixture 在测试退出时确保资源清理（删除创建的对象）。
#
# 模板（按业务场景复制并改写）：
#
# @pytest.fixture
# def created_resource_id(suite_client, super_token) -> str:
#     """创建资源并返回其 ID；测试结束后删除该资源。
#
#     用法：在测试中通过 resource_id 引用，链尾自动清理。
#     """
#     # 1. 调创建接口
#     # resp = suite_client.post("/resources", json={...}, headers={"Authorization": f"Bearer {super_token}"})
#     # resource_id = resp.json()["id"]
#     # yield resource_id
#     # 2. 链尾清理
#     # suite_client.delete(f"/resources/{resource_id}", headers={"Authorization": f"Bearer {super_token}"})
#     yield "PLACEHOLDER_RESOURCE_ID"


# ---------------------------------------------------------------------------
# 并发 helper 模板（L5 异常韧性用）
# ---------------------------------------------------------------------------
#
# 并发竞争 / 幂等性测试需要批量并发发请求并收集结果。
# 推荐：concurrent.futures.ThreadPoolExecutor 或 locust（性能场景）。
#
# 模板（按场景复制并改写）：
#
# @contextlib.contextmanager
# def concurrent_runner(fn, n: int = 10):
#     """并发执行 fn 共 n 次，yield 结果列表。
#
#     用法：
#         with concurrent_runner(lambda: suite_client.get("/ping")) as results:
#             ...  # 在 with 体内已发起 n 个并发请求
#         # 退出 with 后 results 是 [resp1, resp2, ...]
#     """
#     from concurrent.futures import ThreadPoolExecutor, as_completed
#     with ThreadPoolExecutor(max_workers=n) as pool:
#         futures = [pool.submit(fn) for _ in range(n)]
#         yield [f.result() for f in as_completed(futures)]
