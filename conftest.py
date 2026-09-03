"""根目录 conftest：导入 common.fixtures，配置 pytest 全局。"""

from __future__ import annotations

# 显式导入 common.fixtures，使全局 fixture 在所有用例中可见
from common.fixtures import (  # noqa: F401
    _setup_logging,
    api_context,
    auth_manager,
    auth_token,
    suite_client,
    suite_config,
)

# pytest 配置项在 pyproject.toml 的 [tool.pytest.ini_options] 中声明，
# 此处仅负责 fixture 暴露，避免重复声明 markers。
