"""perf 模块级 conftest：暴露性能测试所需的 fixture 骨架。

依赖：
- shared.apijson.api_catalog.get_default_catalog()：从默认 spec 解析 endpoint 列表
- 根 conftest 的 suite_client / auth_manager：复用认证与 HTTP 客户端

【约束】本文件是**框架骨架**：fixture 体用注释占位，不写空实现。
等具体被测系统落地后，按注释指引放开实现。
"""

from __future__ import annotations

import pytest

from shared.apijson.api_catalog import get_default_catalog


@pytest.fixture(scope="session")
def perf_endpoints() -> list[str]:
    """性能测试 endpoint 枚举：从默认 OpenAPI spec 解析所有 endpoint。

    返回形如 ["GET /users", "POST /users/login"] 的列表。
    无 spec 时返回空列表（具体压测用例应自行 skip）。
    """
    return get_default_catalog().list_endpoints()


# ---------------------------------------------------------------------------
# 压测 fixture 骨架
# ---------------------------------------------------------------------------
#
# 选型：locust（分布式压测）或 concurrent.futures（轻量进程内并发）。
# 两种方式都通过复用根 conftest 的 auth_manager 注入鉴权头。
#
# 方式 A：locust（推荐用于阶梯式并发、长时间稳定性测试）
#
# from locust import HttpUser, task, between
#
# class SuiteUser(HttpUser):
#     """复用 common 配置 + RuoYi 认证的 locust 用户。
#
#     部署 locust 时单独跑（不走 pytest 收集）。
#     """
#     wait_time = between(0.5, 1.0)
#
#     def on_start(self):
#         from common.config import get_config
#         from shared.auth.ruoyi_auth import RuoYiAuthProvider
#         config = get_config()
#         auth = RuoYiAuthProvider(config)
#         self.client.headers = {
#             "Authorization": f"Bearer {auth.token}",
#             **auth.extra_headers(),
#         }
#
#     @task
#     def hit_endpoint(self):
#         # 从 perf_endpoints 取一个 endpoint 发请求
#         ...
#
# 方式 B：concurrent.futures（推荐用于 pytest 内的轻量并发测试）
#
# @pytest.fixture
# def concurrent_runner(suite_client, auth_manager):
#     """返回一个 fn(n, endpoint) -> list[resp] 的并发执行器。
#
#     用法：
#         def test_perf_concurrent(concurrent_runner, perf_endpoints):
#             results = concurrent_runner(n=20, endpoint=perf_endpoints[0])
#             assert all(r.status_code == 200 for r in results)
#     """
#     from concurrent.futures import ThreadPoolExecutor, as_completed
#     def _run(n: int, endpoint: str):
#         method, path = endpoint.split(" ", 1)
#         headers = {"Authorization": f"Bearer {auth_manager.token}", **auth_manager.extra_headers()}
#         with ThreadPoolExecutor(max_workers=n) as pool:
#             futures = [
#                 pool.submit(lambda: suite_client.request(method, path, headers=headers))
#                 for _ in range(n)
#             ]
#             return [f.result() for f in as_completed(futures)]
#     return _run


# ---------------------------------------------------------------------------
# 报告输出指引
# ---------------------------------------------------------------------------
#
# 性能测试结果建议挂到 allure：
# - 用 @allure.step 包裹每个压测阶段
# - 用 allure.attach 挂载 CSV / JSON 结果（RPS / P50 / P95 / 错误率）
# - 用 allure.attach 挂载 locust 报告 HTML（如使用 locust）
#
# 模板：
#
# import allure
# import csv
# from io import StringIO
#
# @allure.step("输出压测结果")
# def _attach_perf_report(rows: list[dict]):
#     buf = StringIO()
#     writer = csv.DictWriter(buf, fieldnames=rows[0].keys())
#     writer.writeheader()
#     writer.writerows(rows)
#     allure.attach(buf.getvalue(), name="perf_report",
#                   attachment_type=allure.attachment_type.CSV)
