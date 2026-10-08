"""RuoYi-Cloud-Plus 项目特定配置：从 .env 读 RuoYi 登录所需字段。

显式声明假设：本文件假设被测系统是 RuoYi-Cloud-Plus 5.x。
common 层不感知这些字段，仅通过 AuthProvider 抽象持有实例。

注：未重写 settings_customise_sources，用默认优先级（env > dotenv）。
理由：LOGIN_RSA_PUBKEY/LOGIN_CLIENTID/TEST_TENANT_ID 不是 Windows 内置
环境变量，不会被系统 env 覆盖，默认顺序即可正确从 .env 读取。
SuiteConfig 重写优先级是为了避免 USERNAME 等 Windows 内置变量冲突，
RuoYi 字段无此问题。
"""

from __future__ import annotations

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class RuoYiConfig(BaseSettings):
    """RuoYi-Cloud-Plus 登录配置：tenantId / RSA 公钥 / clientId。"""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
        enable_decoding=False,
    )

    TEST_TENANT_ID: str | None = Field(
        None, description="测试租户 ID，RuoYi 登录 body 的 tenantId 字段，默认 000000"
    )
    LOGIN_RSA_PUBKEY: str = Field(
        "MFwwDQYJKoZIhvcNAQEBBQADSwAwSAJBAKoR8mX0rGKLqzcWmOzbfj64K8ZIgOdHnzkXSOVOZbFu/TJhZ7rFAN+eaGkl3C4buccQd/EjEsj9ir7ijT7h96MCAwEAAQ==",
        description="登录 RSA 公钥 base64 串（前端硬编码），512-bit RSA",
    )
    LOGIN_CLIENTID: str = Field(
        "e5cd7e4891bf95d1d19206ce24a7b32e",
        description="RuoYi clientid 头与登录 body 的 clientId 字段（前端硬编码，对应 sys_client 表的 client_id）",
    )


@lru_cache(maxsize=1)
def get_ruoyi_config() -> RuoYiConfig:
    """RuoYi 配置单例，进程内复用。"""
    return RuoYiConfig()  # type: ignore[call-arg]
