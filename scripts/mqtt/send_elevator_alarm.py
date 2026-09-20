"""按 DEVICE_TYPE 发送对应 payload JSON，时间戳自动刷新为当前时间。

用法：改 DEVICE_ID / DEVICE_TYPE 两个参数 → Run。
"""

import json
import time
from pathlib import Path

from common.mqtt_publisher import MqttPublisher

# ============ 参数（改这里） ============
DEVICE_ID = "342401003"
DEVICE_TYPE = "elevator_report"
# 可选值：
#   water_meter_report    -> WATER/METER/{id}/upload
#   electric_meter_report -> CET/PMC-350/{id}/upload
#   elevator_report       -> ELEVATOR/PROPERTY/{id}/upload
#   elevator_alarm        -> ELEVATOR/EVENT/{id}/upload
# ========================================

_TOPICS = {
    "water_meter_report": f"WATER/METER/{DEVICE_ID}/upload",
    "electric_meter_report": f"CET/PMC-350/{DEVICE_ID}/upload",
    "elevator_report": f"ELEVATOR/PROPERTY/{DEVICE_ID}/upload",
    "elevator_alarm": f"ELEVATOR/EVENT/{DEVICE_ID}/upload",
}

# data 里需要刷新为当前时间的字段
_TIME_KEYS = ("recTime", "lastReadTime", "dayMaxFlowTime", "fault_time")

TOPIC = _TOPICS[DEVICE_TYPE]
PAYLOAD_FILE = Path(__file__).parent / "payloads" / f"{DEVICE_TYPE}.json"

with MqttPublisher() as pub:
    payload = json.loads(PAYLOAD_FILE.read_text(encoding="utf-8"))
    payload["SN"] = DEVICE_ID
    payload["ts"] = int(time.time())
    for key in _TIME_KEYS:
        if key in payload.get("data", {}):
            payload["data"][key] = payload["ts"]
    pub.publish(TOPIC, payload)
    print(payload)
