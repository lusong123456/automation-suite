"""RuoYi-Cloud-Plus 5.x 认证实现：混合加密登录。

显式假设清单：
- BASE_URL 是根前缀（如 http://host/prod-api），登录路径在此基础拼接 /auth/login
- 登录 body 字段：tenantId/username/password/code/uuid/grantType/clientId
  clientId 驼峰（POJO 字段名严格匹配，小写 clientid 会被忽略导致空）
- code/uuid 空字符串（开发环境关闭验证码）
- 登录 POST 非幂等，不重试
- 响应固定 {code:200, msg, data:{access_token, ...}}；401 刷新一次足够
"""

from __future__ import annotations

import json

import httpx

from common.auth import AuthProvider
from common.config import SuiteConfig, get_config
from common.exceptions import AuthenticationError
from common.logging_conf import get_logger
from shared.auth.config import RuoYiConfig, get_ruoyi_config
from shared.auth.encrypt import encrypt_payload

logger = get_logger("ruoyi_auth")


class RuoYiAuthProvider(AuthProvider):
    """RuoYi-Cloud-Plus 混合加密登录实现。

    流程：
    1. 构造明文 body（tenantId/username/password/code/uuid/grantType/clientId）
    2. 调 encrypt_payload 加密成密文 + encrypt-key
    3. 加三头发请求：isEncrypt=true, clientid, encrypt-key
    4. 解析响应拿 token
    """

    _LOGIN_PATH = "/auth/login"

    def __init__(
        self,
        config: SuiteConfig | None = None,
        ruoyi_config: RuoYiConfig | None = None,
    ) -> None:
        super().__init__(config or get_config())
        self._ruoyi = ruoyi_config or get_ruoyi_config()

    def login(self) -> str:
        url = f"{self._config.BASE_URL}{self._LOGIN_PATH}"
        tenant_id = self._ruoyi.TEST_TENANT_ID or "000000"

        # 明文 body：clientId 驼峰（POJO 严格匹配）
        plaintext_body = json.dumps(
            {
                "tenantId": tenant_id,
                "username": self._config.USERNAME,
                "password": self._config.PASSWORD,
                "code": "",
                "uuid": "",
                "grantType": "password",
                "clientId": self._ruoyi.LOGIN_CLIENTID,
            },
            separators=(",", ":"),
            ensure_ascii=False,
        )

        encrypted = encrypt_payload(plaintext_body, self._ruoyi.LOGIN_RSA_PUBKEY)

        headers = {
            "Content-Type": "application/json;charset=UTF-8",
            "clientid": self._ruoyi.LOGIN_CLIENTID,
            "isEncrypt": "true",
            "encrypt-key": encrypted.encrypt_key,
        }

        logger.info(
            "登录请求 POST %s (user=%s, tenant=%s, encrypt=true, aes_key_len=%d)",
            url,
            self._config.USERNAME,
            tenant_id,
            len(encrypted.aes_key),
        )
        # 注意：用 content= 而不是 json=，因为 body 是加密后的字符串
        # json= 会再 JSON 序列化一次（加引号转义），破坏密文
        try:
            resp = httpx.post(
                url,
                content=encrypted.body,
                headers=headers,
                timeout=self._config.REQUEST_TIMEOUT,
            )
            resp.raise_for_status()
        except httpx.HTTPError as exc:
            raise AuthenticationError(f"登录请求失败：{exc}") from exc

        data = resp.json()
        # RuoYi-Cloud-Plus 响应结构固定：{code:200, msg, data:{access_token, ...}}
        token = (data.get("data") or {}).get("access_token")
        if not token:
            msg = data.get("msg") or "无 msg 字段"
            raise AuthenticationError(f"登录失败：{msg} (raw={data})")

        assert isinstance(token, str)  # mypy narrowing：RuoYi access_token 一定是 str
        self._token = token
        logger.info("登录成功，token 已缓存")
        return token

    def extra_headers(self) -> dict[str, str]:
        """RuoYi 网关 Sa-Token 客户端隔离：所有请求带 clientid。

        缺失时 HTTP 200 但业务码 401「认证失败，无法访问系统资源」。
        """
        return {"clientid": self._ruoyi.LOGIN_CLIENTID}
