"""OpenAPI 文档目录：放整份 OpenAPI json 文档（手动维护）。

默认文件名 openapi.json，由 ApiCatalog.get_openapi_spec() 加载。
用途：
- contract L2 schemathesis 模糊测试（属性测试）
- perf 压测场景枚举（list_endpoints 解析 paths）
- spec 差异对比（如有多个副本可放多个文件按名取）

不在此处做远程拉取或 MCP 获取——文档由人工落地，保证可重复、可审计。
"""
