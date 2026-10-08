"""api 模块测试用例集合：L3 / L4 / L5 三层分层。

分层与用例命名规则：
- L3 权限隔离：test_authz_*.py
    验证不同身份（超管 / 租户 A / 租户 B / 匿名）对同一接口的访问边界。
    用 super_token / tenant_a_token / tenant_b_token / anonymous_token fixture。
- L4 业务流转：test_workflow_*.py
    验证多接口串联的状态机（创建→查询→更新→删除等），用 state_machine fixture，
    yield 链尾确保资源清理。
- L5 异常韧性：test_resilience_*.py
    验证异常输入 / 并发竞争 / 限流降级 / 幂等性 等场景，用 concurrent_runner helper。

具体测试用例由具体被测系统落地时编写，本框架只暴露 fixture 骨架（见 conftest.py）。
"""
