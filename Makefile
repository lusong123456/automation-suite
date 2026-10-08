.PHONY: install test test-api test-contract test-contract-spec test-contract-fuzz test-perf test-all test-parallel report lint format clean help

PYTHON ?= python

help:
	@echo "Automation-Suite Makefile"
	@echo ""
	@echo "可用目标："
	@echo "  make install              安装 dev + api 依赖（可编辑模式）"
	@echo "  make test                 运行 API 测试（等同 test-api）"
	@echo "  make test-api             运行 API 接口测试（L3/L4/L5）"
	@echo "  make test-contract        运行契约测试总入口（spec + fuzz）"
	@echo "  make test-contract-spec   运行 L0 spec 完整性 / diff 守护"
	@echo "  make test-contract-fuzz   运行 L2 OpenAPI 属性（schemathesis）"
	@echo "  make test-perf            运行性能测试"
	@echo "  make test-all             运行全部测试"
	@echo "  make test-parallel        并行运行 API 测试（4 进程）"
	@echo "  make report               启动 allure 报告服务"
	@echo "  make lint                 ruff + mypy 静态检查"
	@echo "  make format               ruff format 格式化"
	@echo "  make clean                清理缓存与报告"

install:
	$(PYTHON) -m pip install -e ".[dev,api]"

test: test-api

test-api:
	pytest modules/api/tests -v --alluredir=reports/allure --clean-alluredir

test-contract-spec:
	pytest modules/contract/tests/test_openapi_spec_integrity.py modules/contract/tests/test_openapi_spec_diff.py -v --alluredir=reports/allure --clean-alluredir

test-contract-fuzz:
	pytest modules/contract/tests/test_openapi_props.py -v --alluredir=reports/allure --clean-alluredir

test-contract: test-contract-spec test-contract-fuzz

test-perf:
	# perf 模块当前为骨架，无具体 test_*.py 时 pytest 返回 exit 5（no tests）；
	# 视为正常通过，仅在真正的测试失败时 exit 非 0
	pytest modules/perf/tests -v --alluredir=reports/allure --clean-alluredir || [ $$? -eq 5 ]

test-all:
	pytest modules/ -v --alluredir=reports/allure --clean-alluredir

test-parallel:
	pytest modules/api/tests -v -n 4

report:
	allure serve reports/allure

lint:
	ruff check . && mypy .

format:
	ruff format .

clean:
	rm -rf .pytest_cache .ruff_cache .mypy_cache
	rm -rf reports/allure reports/logs
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
