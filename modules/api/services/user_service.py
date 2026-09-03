"""UserService：用户相关接口封装，结合 context 做字段提取与模板渲染。"""

from __future__ import annotations

import httpx
from pydantic import ValidationError

from common.client import SuiteClient
from common.context import ScenarioContext
from common.exceptions import ContextExtractionError
from common.logging_conf import get_logger
from common.reporting import attach_validation_error
from modules.api.models import UserCreateRequest, UserCreateResponse

logger = get_logger("api.user_service")


class UserService:
    """用户服务：create_user / get_user，自动提取 id 并支持模板渲染。"""

    def __init__(self, client: SuiteClient, context: ScenarioContext) -> None:
        self._client = client
        self._ctx = context

    def create_user(self, request: UserCreateRequest) -> UserCreateResponse:
        """POST /api/users 创建用户，提取 id 到上下文 user_id。"""
        payload = request.model_dump()
        logger.info("创建用户 name=%s job=%s", request.name, request.job)

        resp = self._client.post("/api/users", json=payload, with_auth=False)
        resp.raise_for_status()

        body = resp.json()
        try:
            parsed = UserCreateResponse.model_validate(body)
        except ValidationError:
            attach_validation_error(resp.text)
            raise

        # 提取 id 存入上下文，供后续步骤用 {{ user_id }} 渲染
        try:
            self._ctx.extract(body, "$.id", alias="user_id")
        except ContextExtractionError:
            # reqres 返回的 id 可能是 int，统一转 str 存
            self._ctx.set("user_id", str(parsed.id))

        logger.info("用户创建成功 id=%s", parsed.id)
        return parsed

    def get_user(self, user_id: str | None = None) -> dict:
        """GET /api/users/{id} 查询用户。

        Args:
            user_id: 用户 ID。为 None 时从 context 渲染 {{ user_id }}。

        Returns:
            reqres 返回的 data 字段（dict）。
        """
        if user_id is None:
            user_id = self._ctx.render("{{ user_id }}")

        endpoint = f"/api/users/{user_id}"
        logger.info("查询用户 id=%s", user_id)

        resp = self._client.get(endpoint, with_auth=False)
        resp.raise_for_status()
        return resp.json()
