.PHONY: install test test-parallel report lint format clean help

PYTHON ?= python

help:
	@echo "Automation-Suite Makefile"
	@echo ""
	@echo "可用目标："
	@echo "  make install      安装 dev + api 依赖（可编辑模式）"
	@echo "  make test         运行 API 测试"
	@echo "  make test-parallel 并行运行测试（4 进程）"
	@echo "  make report       启动 allure 报告服务"
	@echo "  make lint         ruff + mypy 静态检查"
	@echo "  make format       ruff format 格式化"
	@echo "  make clean        清理缓存与报告"

install:
	$(PYTHON) -m pip install -e ".[dev,api]"

test:
	pytest modules/api/tests -v

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
