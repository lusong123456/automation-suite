"""AuthProvider 抽象基类：定义 token 获取/刷新契约。

common 层只暴露接口与 token 缓存模板，具体被测系统的认证实现
（如 RuoYi 混合加密登录）下沉到 modules/api/auth/。
SuiteClient 通过本抽象持有 AuthProvider 实例，不感知具体系统。
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from common.config import SuiteConfig, get_config


class AuthProvider(ABC):
    """认证提供方抽象。

    子类实现 login()（具体认证协议）与 extra_headers()（网关侧附加头）。
    token 缓存与 refresh 模板在本基类提供。
    """

    def __init__(self, config: SuiteConfig | None = None) -> None:
        self._config: SuiteConfig = config or get_config()
        self._token: str | None = None

    @abstractmethod
    def login(self) -> str:
        """登录并返回 token。子类实现具体认证协议。"""

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

    def extra_headers(self) -> dict[str, str]:
        """附加到所有请求的认证相关头（如网关 clientid）。

        默认空，子类按需 override。SuiteClient 调用此方法获取所有
        应附加到请求的认证头，无需感知具体系统。
        """
        return {}
