# 契约测试模块（contract）

本模块用于守护接口契约：响应结构是否符合约定，防止字段漂移、类型退化。

## 三层契约架构

| 层 | 工具 | 适用场景 | 当前状态 |
|---|---|---|---|
| L1 Schema 守护 | `jsonschema` + 本地 schema 文件 | 单项目防响应漂移 | 已落地，可跑 |
| L2 OpenAPI 属性测试 | `schemathesis` | 被测服务有 OpenAPI 文档 | 骨架占位，默认 skip |
| L3 消费者驱动契约 | `pact-python` | 多团队/多服务互相调用 | 骨架占位，默认 skip |

## 目录结构

```
modules/contract/
├── conftest.py                 # 模块级 fixture（schema 加载）
├── loaders.py                  # schema/openapi/pydantic 模型加载器
├── schemas/                    # L1 本地 schema 文件（"菜单"）
│   ├── user_create_response.json
│   └── user_get_response.json
├── tests/
│   ├── test_schema_guard.py    # L1：实际响应 vs 本地 schema
│   ├── test_openapi_props.py   # L2：schemathesis 自动生成请求（skip）
│   └── test_pact_consumer.py   # L3：消费者写 pact 文件（skip）
└── pacts/                      # L3 pact 文件输出目录（启用 L3 后自动生成）
```

## 快速使用

### 跑全部契约测试

```bash
pytest modules/contract/tests -m contract
```

### 只跑 L1

```bash
pytest modules/contract/tests/test_schema_guard.py -m contract
```

### 新增接口契约

1. 在 `schemas/` 下放一个 JSON Schema 文件，例如 `order_response.json`
2. 在 `conftest.py` 暴露一个 fixture：

   ```python
   @pytest.fixture
   def order_schema() -> dict:
       return load_schema("order_response.json")
   ```

3. 在 `tests/test_schema_guard.py` 或新文件写测试，复用 `suite_client`：

   ```python
   @allure.epic("契约测试")
   @allure.feature("L1 Schema 守护")
   class TestOrderSchemaGuard:
       @pytest.mark.contract
       def test_create_order_schema(self, suite_client, order_schema):
           resp = suite_client.post("/api/orders", json={...}, with_auth=False)
           validator = Draft202012Validator(order_schema)
           errors = sorted(validator.iter_errors(resp.json()), key=lambda e: e.path)
           if errors:
               pytest.fail(...)
   ```

## 与 api 模块的差异

- **api 模块**：已知输入 → 期望输出，验证**业务正确性**（如 `name == request.name`）
- **contract 模块**：任意合法输入 → 响应符合 schema，验证**结构稳定性**（如 `id` 字段存在且类型正确）

两者不冲突，互相补充。

## 复用 common/ 底座

| common 模块 | contract 复用方式 |
|---|---|
| `config.get_config()` | loaders.py 拼接 BASE_URL 拉 OpenAPI |
| `auth.AuthManager` | schemathesis / pact 注入 Bearer token |
| `client.SuiteClient` | L1 直接复用发请求（含 401 刷新、日志、重试） |
| `reporting.attach_json` | 契约失败时 attach 实际响应与违反点 |
| `exceptions.ContractError` | 契约加载失败时抛出 |

## 启用 L2 schemathesis

1. 被测服务必须暴露 OpenAPI 文档（如 `/openapi.json`）
2. `pyproject.toml` 已在 `[project.optional-dependencies] contract` 中预留 `schemathesis`
3. 打开 `tests/test_openapi_props.py`，取消顶部 SCHEMA 注释，删除 skip
4. 跑：`pytest modules/contract/tests/test_openapi_props.py -m contract`

## 启用 L3 pact

1. 多团队/多服务互相调用场景才需要
2. `pyproject.toml` 已在 `[project.optional-dependencies] contract` 中预留 `pact-python`
3. 打开 `tests/test_pact_consumer.py`，按注释中的写法放开
4. provider 端用 `pact-verifier` 跑生成的 pact 文件
