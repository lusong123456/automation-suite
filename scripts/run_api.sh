#!/usr/bin/env bash
# 运行 API 接口测试
set -euo pipefail

cd "$(dirname "$0")/.."

echo "=== 运行 API 接口测试 ==="
pytest modules/api/tests -v \
    --alluredir=reports/allure \
    --clean-alluredir

echo ""
echo "=== 测试完成 ==="
echo "查看报告：allure serve reports/allure"
