"""配置加载：基于 pydantic-settings，支持多环境与 .env。"""

from __future__ import annotations

from enum import Enum
from functools import lru_cache
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from common.exceptions import ConfigError


class EnvEnum(str, Enum):
    """支持的环境枚举。"""

    DEV = "dev"
    TEST = "test"
    STAGING = "staging"


class SuiteConfig(BaseSettings):
    """全局配置模型，从 .env 与环境变量读取。"""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
        # .env 文件优先级高于系统环境变量，避免 Windows 内置 USERNAME 等覆盖配置
        enable_decoding=False,
    )

    # 自定义 settings source：.env 优先于环境变量
    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings,
        env_settings,
        dotenv_settings,
        file_secret_settings,
    ):  # type: ignore[override]
        # 顺序：init > dotenv > env > secret
        return (init_settings, dotenv_settings, env_settings, file_secret_settings)

    BASE_URL: str = Field(..., description="被测系统基础地址")
    USERNAME: str = Field(..., description="登录账号")
    PASSWORD: str = Field(..., description="登录密码")
    ENV: Literal["dev", "test", "staging"] = Field(
        EnvEnum.DEV.value, description="当前环境标识"
    )

    # 请求相关
    REQUEST_TIMEOUT: float = Field(30.0, description="单次请求超时秒数")
    MAX_RETRIES: int = Field(3, description="网络错误最大重试次数")
    RETRY_BASE_DELAY: float = Field(1.0, description="重试退避基准秒数")
    RETRY_MAX_DELAY: float = Field(10.0, description="重试退避上限秒数")

    @field_validator("BASE_URL")
    @classmethod
    def _strip_trailing_slash(cls, v: str) -> str:
        if not v:
            raise ConfigError("BASE_URL 不能为空")
        return v.rstrip("/")

    @field_validator("USERNAME", "PASSWORD")
    @classmethod
    def _non_empty(cls, v: str, info) -> str:
        if not v:
            raise ConfigError(f"{info.field_name} 不能为空")
        return v


@lru_cache(maxsize=1)
def get_config() -> SuiteConfig:
    """获取单例配置，整个进程内复用。"""
    try:
        return SuiteConfig()  # type: ignore[call-arg]
    except Exception as exc:  # noqa: BLE001
        raise ConfigError(f"配置加载失败：{exc}") from exc


def reload_config() -> SuiteConfig:
    """清除缓存后重新加载配置（测试用）。"""
    get_config.cache_clear()
    return get_config()
