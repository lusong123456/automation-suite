# Automation-Suite

Python 自动化测试套件骨架，当前实现 **接口功能测试（api）** 模块，预留 **性能测试（perf）、安全测试（security）、契约测试（contract）** 扩展位。

## 快速开始

```bash
# 1. 安装依赖（dev + api 分组）
make install

# 2. 复制环境配置
cp .env.example .env

# 3. 运行 API 测试
make test

# 4. 查看 Allure 报告
make report
```

## 目录结构

```
automation-suite/
├── common/         # 公共底座（config/client/auth/context/fixtures...）
├── modules/
│   ├── api/        # 接口功能测试（已实现）
│   ├── perf/       # 性能测试（预留）
│   ├── security/   # 安全测试（预留）
│   └── contract/   # 契约测试（预留）
├── data/           # 测试数据（yaml）
├── reports/        # 报告输出（allure + logs，.gitignore）
├── scripts/        # 运行脚本
├── conftest.py     # 根 conftest
├── pyproject.toml  # 依赖分组 + 工具配置
└── Makefile
```

## 技术栈

- pytest + pytest-xdist + pytest-assume
- httpx + pydantic v2 + pydantic-settings
- factory-boy + faker
- allure-pytest
- tenacity（重试）
- jsonpath-ng（响应提取）
- ruff + mypy + pre-commit

## 设计约束

1. 模块隔离：`modules/api/` 只允许 `from common import ...`
2. 无平台代码：禁用 Web 框架与 ORM
3. 配置隔离：所有配置走 `.env`
4. 报告统一：所有测试输出到 `reports/allure/`
