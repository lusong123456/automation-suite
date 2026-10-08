"""接口契约资产层：提供统一的接口信息查询能力（ApiCatalog）。

基于两个静态目录工作：
- openapi/  ：整份 OpenAPI 文档（手动维护，contract 模糊测试 / perf 场景枚举用）
- schemas/ ：按业务域拆开的 JSON Schema（手动维护，关键接口断言 / api / perf 用）

与 common/ 的边界：common 装系统底座；本层只服务接口测试三兄弟。
路径示例：shared/apijson/。
"""
