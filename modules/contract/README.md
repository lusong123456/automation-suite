# 契约测试模块（contract）

本模块为 **预留扩展位**，当前不含可执行代码。

## 未来职责

- 接口契约验证：响应结构是否符合 OpenAPI/Swagger 规范
- 消费者驱动契约测试（CDC）：验证 provider 不破坏 consumer 依赖的字段
- Schema 演进守护：新增字段不破坏旧 consumer

## 计划工具

- [schemathesis](https://schemathesis.readthedocs.io/)：基于 OpenAPI 的自动属性测试
- [pact-python](https://github.com/pact-foundation/pact-python)：消费者驱动契约
- 复用 `common/config` 读取 BASE_URL，复用 `common/auth` 完成认证

## 如何复用 common/ 底座

```python
import schemathesis
from common.config import get_config
from common.auth import AuthManager

config = get_config()
auth = AuthManager(config)

schema = schemathesis.openapi.from_url(f"{config.BASE_URL}/openapi.json")
# 注入认证
schema.auth.set_token(auth.token)
```

## 与 api 模块的差异

- api 模块验证 **特定场景的功能正确性**（已知输入 → 期望输出）
- contract 模块验证 **结构契约**（任意合法输入 → 响应符合 schema）
- contract 由 schemathesis/pact 独立驱动，结果可集成进 allure
