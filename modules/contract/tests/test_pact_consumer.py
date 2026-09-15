"""L3 消费者驱动契约（CDC）测试骨架：pact-python。

启用前置条件：
1. 多团队/多服务互相调用，A 调 B，A 怕 B 改接口弄崩 A
2. 安装 L3 依赖：pip install pact-python
3. 取消下方注释

工作原理（pact）：
- 消费者（调用方）写下"我依赖你的哪几个字段、什么类型"
- 这份期望叫 pact 文件，写到 modules/contract/pacts/
- 提供方（被调方）改接口前，拿 pact 文件验证自己的返回还满不满足
- 不满足就阻止发布

reqres.in 是公开 API，不是我们维护的，没有"我改接口前验证"的场景，
所以 L3 在当前项目用不上。骨架留给将来多服务场景参考。
"""

from __future__ import annotations

import pytest

_PACT_SKIP_REASON = (
    "L3 消费者驱动契约需多团队/多服务场景；reqres.in 是公开 API，无 provider 端发布流程"
)


@pytest.mark.contract
@pytest.mark.skip(reason=_PACT_SKIP_REASON)
def test_pact_consumer_placeholder() -> None:
    """L3 占位：多服务场景下改为下方写法。

    写法（安装 pact-python 后取消注释）：

        import atexit
        from pact import Consumer, Provider

        pact = Consumer("automation-suite").has_pact_with(
            Provider("user-service"),
            pact_dir="modules/contract/pacts",
        )
        # 进程退出时把 pact 文件写到磁盘
        atexit.register(pact.write_pact_file)

        @pytest.mark.contract
        def test_user_create_contract():
            expected = {
                "id": "123",
                "name": "test",
                "job": "qa",
                "createdAt": "2026-09-15",
            }
            (pact
                .given("一个可创建用户的环境")
                .upon_receiving("创建用户请求")
                .with_request("POST", "/api/users", body={"name": "test", "job": "qa"})
                .will_respond_with(201, body=expected))

            with pact:
                # 实际调用 provider
                resp = suite_client.post(
                    "/api/users",
                    json={"name": "test", "job": "qa"},
                    with_auth=False,
                )
                assert resp.json()["job"] == "qa"

    pact 文件写到 pacts/ 后，provider 端用 pact-verifier 跑：
        pact-verifier --pact-url=pacts/automation-suite-user-service.json \\
                      --provider-base-url=https://provider.example.com
    """
    pytest.skip(_PACT_SKIP_REASON)
