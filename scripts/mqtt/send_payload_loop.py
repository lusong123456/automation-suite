"""循环发送设备上报：按 DEVICE_TYPE 读对应 payload JSON，时间戳自动刷新。

用法：改参数 → Run → 看终端滚动 → Ctrl+C 停止。
"""

import copy
import json
import random
import time
from pathlib import Path

from common.mqtt_publisher import MqttPublisher

# ============ 参数（改这里） ============
DEVICE_ID = "342401030"
DEVICE_TYPE = "water_meter_report"
# 可选值：
#   water_meter_report    -> WATER/METER/{id}/upload
#   electric_meter_report -> CET/PMC-350/{id}/upload
#   elevator_report       -> ELEVATOR/PROPERTY/{id}/upload
#   elevator_alarm        -> ELEVATOR/EVENT/{id}/upload

INTERVAL_SECONDS = 2            # 每条间隔（秒）
MAX_COUNT = 100                    # 循环次数；None = 无限循环直到 Ctrl+C
STATUS_MODE = 1                   # 0=offline 1=online 2=随机 online/offline
# 累计量递增参数（电表 kWhImp / 水表 totalFlow+flowPos+flowNet 共用）
CUMULATIVE_INITIAL = 0          # 初始值
CUMULATIVE_STEP_MIN = 3         # 每条最小步长
CUMULATIVE_STEP_MAX = 100       # 每条最大步长
# 每种设备需要递增的字段（共用同一个累计值）
_CUMULATIVE_FIELDS = {
    "electric_meter_report": ("kWhImp",),
    "water_meter_report": ("totalFlow", "flowPos", "flowNet"),
}
# ========================================

_TOPICS = {
    "water_meter_report": f"WATER/METER/{DEVICE_ID}/upload",
    "electric_meter_report": f"CET/PMC-350/{DEVICE_ID}/upload",
    "elevator_report": f"ELEVATOR/PROPERTY/{DEVICE_ID}/upload",
    "elevator_alarm": f"ELEVATOR/EVENT/{DEVICE_ID}/upload",
}

# 2026年固定120个时间戳（每月10个），循环时按顺序取
_FIXED_TS = [
    1767240000, 1767499200, 1767758400, 1768017600, 1768276800, 1768536000, 1768795200, 1769054400, 1769313600, 1769572800,  # 1月
    1769918400, 1770091200, 1770350400, 1770609600, 1770868800, 1771128000, 1771300800, 1771560000, 1771819200, 1772078400,  # 2月
    1772337600, 1772596800, 1772856000, 1773115200, 1773374400, 1773633600, 1773892800, 1774152000, 1774411200, 1774670400,  # 3月
    1775016000, 1775275200, 1775534400, 1775793600, 1776052800, 1776312000, 1776571200, 1776830400, 1777089600, 1777348800,  # 4月
    1777608000, 1777867200, 1778126400, 1778385600, 1778644800, 1778904000, 1779163200, 1779422400, 1779681600, 1779940800,  # 5月
    1780286400, 1780545600, 1780804800, 1781064000, 1781323200, 1781582400, 1781841600, 1782100800, 1782360000, 1782619200,  # 6月
    1782878400, 1783137600, 1783396800, 1783656000, 1783915200, 1784174400, 1784433600, 1784692800, 1784952000, 1785211200,  # 7月
    1785556800, 1785816000, 1786075200, 1786334400, 1786593600, 1786852800, 1787112000, 1787371200, 1787630400, 1787889600,  # 8月
    1788235200, 1788494400, 1788753600, 1789012800, 1789272000, 1789531200, 1789790400, 1790049600, 1790308800, 1790568000,  # 9月
    1790827200, 1791086400, 1791345600, 1791604800, 1791864000, 1792123200, 1792382400, 1792641600, 1792900800, 1793160000,  # 10月
    1793505600, 1793764800, 1794024000, 1794283200, 1794542400, 1794801600, 1795060800, 1795320000, 1795579200, 1795838400,  # 11月
    1796097600, 1796356800, 1796616000, 1796875200, 1797134400, 1797393600, 1797652800, 1797912000, 1798171200, 1798430400,  # 12月
]

# data 里需要刷新时间戳的字段
_TIME_KEYS = ("recTime", "lastReadTime", "dayMaxFlowTime", "fault_time")

# data 里需要定制修改的业务参数（待确认物模型后补充）
_CUSTOM_KEYS: tuple[str, ...] = ()


def _customize(data: dict, count: int) -> None:
    """按物模型定制修改 data 参数（原地修改，每条消息调用一次）。

    TODO: 待确认各设备物模型后补充定制逻辑，例如：
    - 累计量递增（totalFlow / kWhImp）
    - 快照量随机（instFlow / Ua / carPosition）
    - 告警位翻转
    """
    pass


TOPIC = _TOPICS[DEVICE_TYPE]
PAYLOAD_FILE = Path(__file__).parent / "payloads" / f"{DEVICE_TYPE}.json"

with MqttPublisher() as pub:
    template = json.loads(PAYLOAD_FILE.read_text(encoding="utf-8"))
    # 根据模板里 SN 的原始类型决定转换方式
    _sn_is_int = isinstance(template.get("SN"), int)
    count = 0
    cumulative_current = CUMULATIVE_INITIAL
    cum_fields = _CUMULATIVE_FIELDS.get(DEVICE_TYPE, ())
    while MAX_COUNT is None or count < MAX_COUNT:
        payload = copy.deepcopy(template)
        payload["SN"] = int(DEVICE_ID) if _sn_is_int else DEVICE_ID
        payload["ts"] = int(time.time())   # 实时时间
        # payload["ts"] = _FIXED_TS[count % len(_FIXED_TS)]
        payload["status"] = (
            "offline" if STATUS_MODE == 0
            else "online" if STATUS_MODE == 1
            else random.choice(["online", "offline"])
        )
        if cum_fields:
            cumulative_current = round(cumulative_current + random.uniform(CUMULATIVE_STEP_MIN, CUMULATIVE_STEP_MAX), 2)
            for key in cum_fields:
                payload["data"][key] = cumulative_current
        for key in _TIME_KEYS:
            if key in payload.get("data", {}):
                payload["data"][key] = payload["ts"]
        _customize(payload["data"], count)

        pub.publish(TOPIC, payload)
        extra = f" cum={cumulative_current}" if cum_fields else ""
        print(f"[{count:03d}] topic={TOPIC} status={payload['status']}{extra} ts={payload['ts']}")
        count += 1
        time.sleep(INTERVAL_SECONDS)
