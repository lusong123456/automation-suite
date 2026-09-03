# 性能测试模块（perf）

本模块为 **预留扩展位**，当前不含可执行代码。

## 未来职责

- 接口压力测试：阶梯式并发验证吞吐量与延迟
- 稳定性测试：长时间持续负载下的内存泄漏与连接耗尽检测
- 容量规划：找出系统拐点与最大承载

## 计划工具

- [locust](https://locust.io/)：Python 编写的分布式压测框架
- 复用 `common/client.SuiteClient` 的认证与重试逻辑（通过 locust 的 HttpUser 包装）

## 如何复用 common/ 底座

```python
from common.config import get_config
from common.auth import AuthManager

class SuiteUser(HttpUser):
    def on_start(self):
        config = get_config()
        auth = AuthManager(config)
        self.client.headers = {"Authorization": f"Bearer {auth.token}"}
```

## 与 api 模块的差异

- api 模块关注 **正确性**（断言响应结构与值）
- perf 模块关注 **性能指标**（RPS、P95 延迟、错误率）
- perf 不使用 pytest 执行，由 locust 独立运行
- 结果不输出到 allure，而是 locust 自有报告 + CSV
