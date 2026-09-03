# 安全测试模块（security）

本模块为 **预留扩展位**，当前不含可执行代码。

## 未来职责

- OWASP Top 10 自动化扫描（注入、XSS、越权、敏感信息泄漏）
- 认证与授权测试（token 复用、垂直/水平越权）
- 接口限流与防刷验证

## 计划工具

- [OWASP ZAP](https://www.zaproxy.org/) + `python-zaproxy`：主动/被动扫描
- 复用 `common/client.SuiteClient` 构造已认证请求
- 复用 `common/auth.AuthManager` 切换不同身份用户做越权测试

## 如何复用 common/ 底座

```python
from common.client import SuiteClient
from common.auth import AuthManager

# 用合法用户身份构造请求
client = SuiteClient(auth=AuthManager())
# 注入 payload 做模糊测试
resp = client.get("/api/users/1' OR '1'='1")
```

## 与 api 模块的差异

- api 模块验证 **功能正确性**
- security 模块验证 **安全性**（能否被滥用）
- 扫描结果由 ZAP 生成 HTML 报告，不进入 allure
