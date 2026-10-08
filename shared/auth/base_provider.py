"""多身份认证提供方契约：AuthProvider 抽象基类。

这是**框架层契约**（不是具体被测系统实现）。modules/api 的 L3 权限隔离、
L4 业务流转、L5 异常韧性测试需要按身份（超管 / 租户 A / 租户 B / 匿名）
切换 token，本基类定义该切换的最小契约。

与 common.auth.AuthProvider 的关系：
- common.auth.AuthProvider：底层 token 缓存模板（login/refresh/clear/extra_headers）
- shared.auth.base_provider.AuthProvider：上层多身份契约
  （login/get_token/switch_tenant/clear_tenant/get_identity）

子类按被测系统实现本契约（如 shared/auth/ruoyi_auth.py 的升级版本），
具体实现可同时继承 common.auth.AuthProvider 复用 token 缓存能力。
modules/api/conftest.py 中多身份 fixture 通过 get_identity(identity) 取对应 token。
"""

from __future__ import annotations

from abc import ABC, abstractmethod


class AuthProvider(ABC):
    """多身份认证提供方契约（框架层抽象基类）。

    子类需实现：
    - login()           ：登录拿 token
    - get_token()       ：取当前上下文 token
    - switch_tenant()   ：动态切换租户
    - clear_tenant()    ：清理租户上下文
    - get_identity()    ：按 identity key 取对应身份 token

    identity 取值约定：super / tenant_a / tenant_b / anonymous。
    具体身份到账号的映射在子类配置中完成。
    """

    @abstractmethod
    def login(self) -> str:
        """登录并返回 token。子类实现具体认证协议。"""

    @abstractmethod
    def get_token(self) -> str:
        """取当前上下文 token。未登录时由子类决定是否自动登录。"""

    @abstractmethod
    def switch_tenant(self, tenant_id: str) -> None:
        """动态切换租户上下文。后续 get_token / get_identity 应反映新租户。"""

    @abstractmethod
    def clear_tenant(self) -> None:
        """清理租户上下文（恢复默认租户 / 退出多租户模式）。"""

    @abstractmethod
    def get_identity(self, identity: str) -> str:
        """按 identity key 取对应身份 token。

        identity ∈ {"super", "tenant_a", "tenant_b", "anonymous"}。
        子类负责为每个 identity 绑定账号 / 凭据并缓存 token。
        """
