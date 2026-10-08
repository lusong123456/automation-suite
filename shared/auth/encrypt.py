"""RuoYi-Cloud-Plus 混合加密：AES-ECB-256 + RSA-PKCS1。

扒自 IoT 平台前端 `assets/user-CD10iO_L.js`（已直接 grep 源码确认）：

JS 加密链（webpack 压缩，函数名原始）：
- qo()  生成 32 字符随机字符串（[A-Za-z0-9]）
- Jo()  = CryptoJS.enc.Utf8.parse(qo())  → 32 字节 WordArray（AES-256 key）
- Yo(t) = CryptoJS.enc.Base64.stringify(t) → 44 字符 base64（用于 RSA 输入）
- Zo(e, t) = CryptoJS.AES.encrypt(e, t, {mode: ECB, padding: Pkcs7}).toString()
- Dc(e) = new JSEncrypt(); setPublicKey(Tc); encrypt(e)
- Tc = "MFwwDQYJKoZIhvcNAQEBBQADSwAwSAJBAKoR8mX0rGKLqzcWmOzbfj64K8ZIgOdHnzkXSOVOZbFu/TJhZ7rFAN+eaGkl3C4buccQd/EjEsj9ir7ijT7h96MCAwEAAQ=="

axios 请求拦截器（关键 1 行）：
    e.headers[kc] = Dc(Yo(t))     // encrypt-key = RSA加密(base64(AES key))
    e.data = Zo(JSON.stringify(e.data), t)  // body = AES加密(JSON)

关键陷阱（踩过坑）：RSA 加密的不是原始 32 字节 AES key，而是
**32 字节 key 的 base64 字符串（44 字节）**。后端解密 encrypt-key 拿到
base64 字符串，再 Base64.parse 还原成 WordArray 当 AES key 用。
如果 Python 直接 RSA 加密 32 字节原始 key，后端解出非 base64 字符串，
Base64.parse 抛异常 → 500。
"""

from __future__ import annotations

import base64
import secrets
import string
from typing import NamedTuple

from Crypto.Cipher import AES, PKCS1_v1_5
from Crypto.PublicKey import RSA
from Crypto.Util.Padding import pad

# 前端 key 字符集：[A-Za-z0-9]，对应 qo() 的 chars
_KEY_CHARSET = string.ascii_letters + string.digits
# AES key 长度（字符 = 字节，ASCII）：32 → AES-256
# 前端 qo() for(let t=0;t<32;t++)，32 字符 → 32 字节 → AES-256
_KEY_LEN = 32


class EncryptedPayload(NamedTuple):
    """加密结果：body 与 encrypt-key 头。"""

    body: str           # base64(AES-ECB 密文)
    encrypt_key: str    # base64(RSA-PKCS1 密文)
    aes_key: str        # 明文 AES key（仅调试用，生产不要打日志）


def _random_aes_key() -> str:
    """生成 32 字符随机 AES key（对应前端 qo()）。"""
    return "".join(secrets.choice(_KEY_CHARSET) for _ in range(_KEY_LEN))


def _rsa_encrypt(aes_key: str, public_key_b64: str) -> str:
    """RSA-PKCS1Padding 加密「AES key 的 base64 字符串」，输出 base64。

    前端流程：Yo(Jo()) = Base64.stringify(Utf8.parse(qo()))
      = base64(32 字节 key) = 44 字符 base64 字符串
    然后 Dc() 用 RSA-PKCS1 加密这 44 字节字符串。
    后端解密时 Base64.parse 拿到原始 32 字节当 AES key 用。

    注意：RSA 512-bit 公钥 PKCS1 v1.5 最大明文 53 字节，44 字节能装下。
    """
    # 1. aes_key 字符串 → 32 字节 UTF-8 二进制
    aes_key_bytes = aes_key.encode("utf-8")
    # 2. base64 编码 → 44 字符 ASCII 字符串（前端 Yo() 输出）
    base64_str = base64.b64encode(aes_key_bytes).decode("ascii")
    # 3. RSA 加密这 44 字节字符串
    base64_bytes = base64_str.encode("utf-8")  # 44 字节

    # 前端硬编码公钥是 base64 裸串（DER SubjectPublicKeyInfo），包装成 PEM
    der = base64.b64decode(public_key_b64)
    pem = (
        b"-----BEGIN PUBLIC KEY-----\n"
        + base64.b64encode(der)
        + b"\n-----END PUBLIC KEY-----\n"
    )
    rsa_key = RSA.import_key(pem)
    cipher = PKCS1_v1_5.new(rsa_key)
    encrypted = cipher.encrypt(base64_bytes)
    return base64.b64encode(encrypted).decode("ascii")


def _aes_encrypt(plaintext: str, aes_key: str) -> str:
    """AES-ECB/Pkcs7 加密 plaintext，输出 base64。

    对应前端 Zo(e, t)：
        CryptoJS.AES.encrypt(e, t, {
            mode: CryptoJS.mode.ECB,
            padding: CryptoJS.pad.Pkcs7,
        }).toString()
    其中 t = Utf8.parse(qo())（32 字节 WordArray）。
    CryptoJS toString() 默认输出 OpenSSL 格式（无 Salted__ 前缀，因为传了 WordArray key）。
    """
    key_bytes = aes_key.encode("utf-8")  # 32 字符 → 32 字节
    cipher = AES.new(key_bytes, AES.MODE_ECB)
    padded = pad(plaintext.encode("utf-8"), AES.block_size, style="pkcs7")
    encrypted = cipher.encrypt(padded)
    return base64.b64encode(encrypted).decode("ascii")


def encrypt_payload(plaintext: str, rsa_public_key_b64: str) -> EncryptedPayload:
    """加密登录请求 body。

    Args:
        plaintext: 登录请求 JSON 字符串（如 '{"username":"x","password":"y"}'）
        rsa_public_key_b64: RSA 公钥 base64 串（前端硬编码值）

    Returns:
        EncryptedPayload：含加密后 body 和 encrypt-key 头
    """
    aes_key = _random_aes_key()
    body = _aes_encrypt(plaintext, aes_key)
    encrypt_key = _rsa_encrypt(aes_key, rsa_public_key_b64)
    return EncryptedPayload(body=body, encrypt_key=encrypt_key, aes_key=aes_key)
