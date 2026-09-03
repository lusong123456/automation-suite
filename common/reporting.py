"""Allure 附件与日志 attach 统一封装。"""

from __future__ import annotations

import json
from typing import Any

import allure
from httpx import Response

from common.logging_conf import get_logger

logger = get_logger("reporting")


def attach_json(name: str, data: Any) -> None:
    """将 Python 对象格式化为 JSON 并 attach 到 allure。"""
    try:
        body = json.dumps(data, ensure_ascii=False, indent=2, default=str)
    except TypeError:
        body = str(data)
    allure.attach(body=body, name=name, attachment_type=allure.attachment_type.JSON)


def attach_text(name: str, text: str) -> None:
    """附加纯文本到 allure。"""
    allure.attach(body=text, name=name, attachment_type=allure.attachment_type.TEXT)


def attach_request_response(response: Response) -> None:
    """将请求与响应摘要 attach 到 allure，并同步记录日志。"""
    request = response.request
    req_summary = {
        "method": request.method,
        "url": str(request.url),
        "headers": dict(request.headers),
    }
    resp_summary = {
        "status_code": response.status_code,
        "elapsed_ms": round(response.elapsed.total_seconds() * 1000, 2),
        "headers": dict(response.headers),
    }
    try:
        resp_summary["json"] = response.json()
    except Exception:  # noqa: BLE001
        resp_summary["text"] = response.text[:2000]

    logger.info(
        "%s %s -> %s (%.2fms)",
        request.method,
        request.url,
        response.status_code,
        resp_summary["elapsed_ms"],
    )
    attach_json("request", req_summary)
    attach_json("response", resp_summary)


def attach_validation_error(raw_body: str) -> None:
    """pydantic 解析失败时，attach 原始响应体以便排查。"""
    attach_text("raw_response_on_validation_error", raw_body)
    logger.error("pydantic 解析失败，原始响应体已 attach")
