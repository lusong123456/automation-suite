"""SuiteClient：httpx 封装，认证、日志、自动重试、401 自动刷新。"""

from __future__ import annotations

from typing import Any, Optional

import httpx
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from common.auth import AuthManager
from common.config import SuiteConfig, get_config
from common.exceptions import AuthenticationError
from common.logging_conf import get_logger
from common.reporting import attach_request_response

logger = get_logger("client")

# 触发重试的网络异常类型
_RETRYABLE_EXCEPTIONS = (
    httpx.ConnectError,
    httpx.ReadTimeout,
    httpx.RemoteProtocolError,
)


class SuiteClient:
    """统一的 HTTP 客户端封装。

    - 自动注入 Bearer token。
    - 网络异常自动重试（仅幂等方法）。
    - 401 自动刷新 token 并重放一次。
    - 请求/响应日志 + allure 附件。
    """

    def __init__(
        self,
        config: Optional[SuiteConfig] = None,
        auth: Optional[AuthManager] = None,
    ) -> None:
        self._config = config or get_config()
        self._auth = auth or AuthManager(self._config)
        self._client = httpx.Client(timeout=self._config.REQUEST_TIMEOUT)

    # --- 内部辅助 ---

    def _build_headers(
        self,
        extra: Optional[dict[str, str]] = None,
        with_auth: bool = True,
    ) -> dict[str, str]:
        headers = {"Content-Type": "application/json", "Accept": "application/json"}
        if with_auth:
            try:
                headers["Authorization"] = f"Bearer {self._auth.token}"
            except AuthenticationError:
                logger.warning("token 获取失败，请求将不带 Authorization 头")
        if extra:
            headers.update(extra)
        return headers

    def _do_request(
        self,
        method: str,
        endpoint: str,
        *,
        params: Optional[dict[str, Any]] = None,
        json: Optional[Any] = None,
        headers: Optional[dict[str, str]] = None,
        idempotent: bool = False,
        with_auth: bool = True,
        _is_replay: bool = False,
    ) -> httpx.Response:
        """实际发送请求，处理 401 与日志 attach。"""
        url = (
            endpoint
            if endpoint.startswith("http")
            else f"{self._config.BASE_URL}{endpoint}"
        )
        final_headers = self._build_headers(headers, with_auth=with_auth)

        logger.debug("%s %s", method, url)
        resp = self._client.request(
            method=method,
            url=url,
            params=params,
            json=json,
            headers=final_headers,
        )
        attach_request_response(resp)

        # 401 自动刷新并重放一次
        if resp.status_code == 401 and not _is_replay and with_auth:
            logger.warning("收到 401，尝试刷新 token 后重放")
            self._auth.refresh()
            return self._do_request(
                method,
                endpoint,
                params=params,
                json=json,
                headers=headers,
                idempotent=idempotent,
                with_auth=with_auth,
                _is_replay=True,
            )

        return resp

    # --- 公开接口 ---

    def get(self, endpoint: str, **kwargs: Any) -> httpx.Response:
        """GET 请求，幂等可重试。"""

        @retry(
            reraise=True,
            retry=retry_if_exception_type(_RETRYABLE_EXCEPTIONS),
            stop=stop_after_attempt(self._config.MAX_RETRIES),
            wait=wait_exponential(
                multiplier=self._config.RETRY_BASE_DELAY,
                max=self._config.RETRY_MAX_DELAY,
            ),
        )
        def _go() -> httpx.Response:
            return self._do_request("GET", endpoint, **kwargs)

        return _go()

    def put(self, endpoint: str, **kwargs: Any) -> httpx.Response:
        """PUT 请求，幂等可重试。"""

        @retry(
            reraise=True,
            retry=retry_if_exception_type(_RETRYABLE_EXCEPTIONS),
            stop=stop_after_attempt(self._config.MAX_RETRIES),
            wait=wait_exponential(
                multiplier=self._config.RETRY_BASE_DELAY,
                max=self._config.RETRY_MAX_DELAY,
            ),
        )
        def _go() -> httpx.Response:
            return self._do_request("PUT", endpoint, **kwargs)

        return _go()

    def delete(self, endpoint: str, **kwargs: Any) -> httpx.Response:
        """DELETE 请求，幂等可重试。"""

        @retry(
            reraise=True,
            retry=retry_if_exception_type(_RETRYABLE_EXCEPTIONS),
            stop=stop_after_attempt(self._config.MAX_RETRIES),
            wait=wait_exponential(
                multiplier=self._config.RETRY_BASE_DELAY,
                max=self._config.RETRY_MAX_DELAY,
            ),
        )
        def _go() -> httpx.Response:
            return self._do_request("DELETE", endpoint, **kwargs)

        return _go()

    def post(
        self,
        endpoint: str,
        *,
        idempotent: bool = False,
        **kwargs: Any,
    ) -> httpx.Response:
        """POST 请求。

        Args:
            endpoint: 请求路径或完整 URL。
            idempotent: 是否对该 POST 做网络重试。默认 False（业务侧 POST 通常非幂等）。
        """
        if not idempotent:
            return self._do_request("POST", endpoint, **kwargs)

        @retry(
            reraise=True,
            retry=retry_if_exception_type(_RETRYABLE_EXCEPTIONS),
            stop=stop_after_attempt(self._config.MAX_RETRIES),
            wait=wait_exponential(
                multiplier=self._config.RETRY_BASE_DELAY,
                max=self._config.RETRY_MAX_DELAY,
            ),
        )
        def _go() -> httpx.Response:
            return self._do_request("POST", endpoint, idempotent=True, **kwargs)

        return _go()

    # --- 资源管理 ---

    def close(self) -> None:
        """关闭底层 httpx 连接池。"""
        self._client.close()
        logger.info("SuiteClient 已关闭")

    def __enter__(self) -> "SuiteClient":
        return self

    def __exit__(self, exc_type: object, exc: object, tb: object) -> None:
        self.close()
