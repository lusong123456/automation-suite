#!/usr/bin/env bash
# 运行所有已实现的测试模块（当前仅 api）
set -euo pipefail

cd "$(dirname "$0")/.."

echo "=== 运行全部测试 ==="
pytest modules/ -v \
    --alluredir=reports/allure \
    --clean-alluredir

echo ""
echo "=== 全部测试完成 ==="
echo "查看报告：allure serve reports/allure"
