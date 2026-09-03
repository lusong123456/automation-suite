"""AuthManager：登录缓存 token，401 自动刷新。"""

from __future__ import annotations

from typing import Optional

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from common.config import SuiteConfig, get_config
from common.exceptions import AuthenticationError
from common.logging_conf import get_logger

logger = get_logger("auth")

# 认证管理类
class AuthManager:
    """认证管理：登录、缓存 token、401 自动重新登录。

    生命周期与 session 级 fixture 一致，进程内全局复用。
    """

    def __init__(self, config: Optional[SuiteConfig] = None) -> None:
        self._config = config or get_config()
        self._token: Optional[str] = None

    @retry(
        reraise=True,
        stop=stop_after_attempt(2),
        wait=wait_exponential(multiplier=1, min=1, max=5),
    )
    def login(self) -> str:
        """调用 /api/login 获取 token 并缓存。"""
        url = f"{self._config.BASE_URL}/api/login"
        payload = {"email": self._config.USERNAME, "password": self._config.PASSWORD}
        logger.info("登录请求 POST %s (user=%s)", url, self._config.USERNAME)

        try:
            resp = httpx.post(url, json=payload, timeout=self._config.REQUEST_TIMEOUT)
            resp.raise_for_status()
        except httpx.HTTPError as exc:
            raise AuthenticationError(f"登录请求失败：{exc}") from exc

        data = resp.json()
        token = data.get("token")
        if not token:
            raise AuthenticationError(f"登录响应未包含 token：{data}")

        self._token = token
        logger.info("登录成功，token 已缓存")
        return token

    @property
    def token(self) -> str:
        """获取当前 token，未登录时自动登录。"""
        if self._token is None:
            self.login()
        assert self._token is not None  # mypy narrowing
        return self._token

    def refresh(self) -> str:
        """强制重新登录刷新 token。"""
        self._token = None
        return self.login()

    def clear(self) -> None:
        """清除缓存的 token。"""
        self._token = None
