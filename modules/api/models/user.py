"""用户相关 pydantic 模型与 factory-boy 工厂。

字段对齐 https://reqres.in 实际返回结构：
- POST /api/users 请求：{ "name": str, "job": str }
- POST /api/users 响应：{ "id": str, "name": str, "job": str, "createdAt": str }
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

import factory
from faker import Faker
from pydantic import BaseModel, ConfigDict, Field, field_validator

faker = Faker()


class UserCreateRequest(BaseModel):
    """创建用户请求模型。"""

    model_config = ConfigDict(extra="forbid")

    name: str = Field(..., min_length=1, description="用户名")
    job: str = Field(..., min_length=1, description="职位")

    @field_validator("name", "job")
    @classmethod
    def _non_empty_stripped(cls, v: str, info: Any) -> str:
        cleaned = v.strip()
        if not cleaned:
            raise ValueError(f"{info.field_name} 不能为空白字符")
        return cleaned


class UserCreateResponse(BaseModel):
    """创建用户响应模型（对齐 reqres 返回）。"""

    model_config = ConfigDict(extra="ignore")

    id: str = Field(..., description="用户 ID")
    name: str
    job: str
    createdAt: str = Field(..., description="创建时间")

    @field_validator("id")
    @classmethod
    def _id_non_empty(cls, v: str) -> str:
        if not v:
            raise ValueError("id 不能为空")
        return v


class UserCreateRequestFactory(factory.Factory):
    """factory-boy + faker 工厂，生成随机 UserCreateRequest 字典。"""

    class Meta:
        model = UserCreateRequest

    name = factory.LazyFunction(lambda: faker.name())
    job = factory.LazyFunction(lambda: faker.job())


if __name__ == "__main__":
    # 自测：手动验证工厂可用
    req = UserCreateRequestFactory.build()
    print(req.model_dump())
    assert req.name and req.job
    print("factory 自测通过")
