"""MqttPublisher：paho-mqtt 2.x 封装，连接 → 发布 → 断开。"""

from __future__ import annotations

import json
from typing import Any

import paho.mqtt.client as mqtt
from paho.mqtt.enums import CallbackAPIVersion
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from common.exceptions import MqttError
from common.logging_conf import get_logger

logger = get_logger("mqtt")


class MqttConfig(BaseSettings):
    """MQTT 配置，从 .env 读取，env_prefix=MQTT_ 自动映射。"""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="MQTT_",
        extra="ignore",
    )

    BROKER_HOST: str = Field("broker.emqx.io", description="broker 地址")
    BROKER_PORT: int = Field(1883, description="broker 端口")
    BROKER_USERNAME: str = Field("", description="用户名，空=匿名")
    BROKER_PASSWORD: str = Field("", description="密码，空=匿名")
    CLIENT_ID: str = Field("automation-suite-01", description="客户端 ID，需唯一")
    KEEPALIVE: int = Field(60, description="心跳秒数")
    DEFAULT_QOS: int = Field(1, description="默认 QoS：0/1/2")
    CONNECT_TIMEOUT: float = Field(10.0, description="连接超时秒数")


class MqttPublisher:
    """MQTT 消息发布器：连接 broker，发消息，退出自动断开。

    用法::

        with MqttPublisher() as pub:
            pub.publish("/sensor/temp", "26.5")
            pub.publish("/status", {"online": True})   # dict 自动转 JSON
    """

    def __init__(self, config: MqttConfig | None = None) -> None:
        self._config = config or MqttConfig()
        self._client: mqtt.Client | None = None

    def _ensure_connected(self) -> mqtt.Client:
        """懒连接：第一次 publish 时才连 broker。"""
        if self._client is not None:
            return self._client

        cfg = self._config
        client = mqtt.Client(
            callback_api_version=CallbackAPIVersion.VERSION2,
            client_id=cfg.CLIENT_ID,
        )
        if cfg.BROKER_USERNAME:
            client.username_pw_set(cfg.BROKER_USERNAME, cfg.BROKER_PASSWORD)

        logger.info("连接 MQTT broker %s:%s", cfg.BROKER_HOST, cfg.BROKER_PORT)
        result = client.connect(
            cfg.BROKER_HOST,
            cfg.BROKER_PORT,
            keepalive=cfg.KEEPALIVE,
        )
        if result != mqtt.MQTT_ERR_SUCCESS:
            raise MqttError(f"连接失败，rc={result}")

        # 启动后台网络循环（paho 靠这个收发心跳和 ACK）
        client.loop_start()
        self._client = client
        logger.info("MQTT 已连接 client_id=%s", cfg.CLIENT_ID)
        return client

    def publish(
        self,
        topic: str,
        payload: str | bytes | dict[str, Any],
        *,
        qos: int | None = None,
        retain: bool = False,
    ) -> None:
        """发一条消息。

        Args:
            topic: 发布主题。
            payload: 负载。dict 自动转 JSON 字符串，str/bytes 原样发送。
            qos: 服务质量等级 0/1/2，默认走配置 MQTT_DEFAULT_QOS。
            retain: 是否保留消息（新订阅者上线后能收到最后一条 retain）。
        """
        client = self._ensure_connected()
        q = qos if qos is not None else self._config.DEFAULT_QOS

        if isinstance(payload, dict):
            payload = json.dumps(payload, ensure_ascii=False)

        info = client.publish(topic, payload, qos=q, retain=retain)
        # 阻塞等待真正发出（qos=0 立即返回，qos>=1 等 PUBACK）
        info.wait_for_publish()

        if info.rc != mqtt.MQTT_ERR_SUCCESS:
            raise MqttError(f"发布失败 topic={topic} rc={info.rc}")
        logger.info("已发布 topic=%s qos=%s mid=%s", topic, q, info.mid)

    def publish_batch(
        self,
        messages: list[dict[str, Any]],
    ) -> None:
        """批量发送：``[{"topic": "...", "payload": "...", "qos": 1}, ...]``

        复用同一条连接，避免每条消息都 reconnect。
        """
        for msg in messages:
            self.publish(
                msg["topic"],
                msg["payload"],
                qos=msg.get("qos"),
                retain=msg.get("retain", False),
            )

    def disconnect(self) -> None:
        """断开连接。"""
        if self._client is not None:
            self._client.loop_stop()
            self._client.disconnect()
            self._client = None
            logger.info("MQTT 已断开")

    def __enter__(self) -> "MqttPublisher":
        return self

    def __exit__(self, *exc: object) -> None:
        self.disconnect()
