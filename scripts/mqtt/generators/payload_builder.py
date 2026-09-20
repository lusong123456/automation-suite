"""payload 生成器：用策略字典分发，加新策略只要在 STRATEGIES 里加一行。

写新策略的步骤：
1. 定义函数 ``def my_strategy(count: int, device_id: str) -> dict``
2. 在 STRATEGIES 字典里加 ``"my_strategy": my_strategy``
3. 脚本头部 ``GENERATOR_MODE = "my_strategy"`` 即可使用

timestamp 统一用 Unix 时间戳（整数秒），嵌入式设备和业务系统都好处理。
"""

from __future__ import annotations

import json
import random
import time
from pathlib import Path


_PAYLOADS_DIR = Path(__file__).resolve().parents[1] / "payloads"
_MODELS_DIR = Path(__file__).resolve().parents[1] / "models"


def _now_ts() -> int:
    """Unix 时间戳（秒），整数。"""
    return int(time.time())


# ====== 设备类型 → JSON 文件映射 ======

DEVICE_TYPE_MAP: dict[str, str] = {
    "water_meter": "water_meter_report_.json",
    "electric_meter": "electric_meter_report.json",
    "elevator": "elevator_report.json",
}

# 物模型文件名映射
_MODEL_FILE_MAP: dict[str, str] = {
    "water_meter": "model_water_meter.json",
    "electric_meter": "model_eletric_meter.json",
    "elevator": "model_elevator.json",
}


def _load_device_template(device_type: str) -> dict:
    """根据 device_type 从 payloads/ 读 JSON 模板。"""
    if device_type not in DEVICE_TYPE_MAP:
        raise ValueError(
            f"未知 device_type: {device_type!r}, 可用: {list(DEVICE_TYPE_MAP)}"
        )
    path = _PAYLOADS_DIR / DEVICE_TYPE_MAP[device_type]
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _load_device_model(device_type: str) -> dict:
    """根据 device_type 从 models/ 读物模型定义。"""
    if device_type not in _MODEL_FILE_MAP:
        raise ValueError(
            f"未知 device_type: {device_type!r}, 可用: {list(_MODEL_FILE_MAP)}"
        )
    path = _MODELS_DIR / _MODEL_FILE_MAP[device_type]
    with open(path, encoding="utf-8") as f:
        return json.load(f)


# ====== 按物模型 specs 生成随机值 ======

# 这些字段是时间戳，用当前时间而非随机
_TIMESTAMP_FIELDS = {"recTime", "lastReadTime", "dayMaxFlowTime"}

# 累计量字段：只增不减。特征名 → 增量范围（min_step, max_step）
# 增量单位与物模型 step 一致
_CUMULATIVE_FIELDS: dict[str, tuple[float, float]] = {
    # === 水表 ===
    "totalFlow": (0.001, 0.5),          # 每小时加 0~0.5 m³
    "flowPos": (0.001, 0.5),
    "flowNet": (0.001, 0.5),
    "flowToday": (0.001, 0.3),
    "flowMonth": (0.001, 0.5),
    "flowSettle": (0.001, 0.5),
    "dayMaxFlow": (0.0, 0.0),           # 今天最大值，正常不增，偶尔被 instFlow 超越
    "upTime": (0, 1),                   # 小时
    "workTime": (0, 1),
    "readCnt": (0, 1),

    # === 电表 ===
    "kWhImp": (0.001, 0.5),             # 正向有功电能 kWh
    "kWhExp": (0.001, 0.1),             # 反向（一般很少）
    "kvarhImp": (0.001, 0.3),
    "kvarhExp": (0.001, 0.1),
    "kWhImpCt": (0, 0),                 # 翻转次数，极罕见
    "kWhExpCt": (0, 0),
    "kvarhImpCt": (0, 0),
    "kvarhExpCt": (0, 0),

    # === 电梯 ===
    "accumulativeRunNum": (0, 1),       # 累计运行次数
    "accumulativeRunTime": (0, 5),       # 累计运行时间（秒）
    "doorOpenCloseCount": (0, 1),       # 开关门次数
    "travelDistance": (0.0, 5.0),        # 累计里程 km
    "upTime": (0, 1),
    "workTime": (0, 1),
    "readCnt": (0, 1),
}

# 物模型 specs 里 max 很大（> 1000）且 min=0 的，默认视为累计量
def _looks_cumulative(specs: dict) -> bool:
    lo = float(specs.get("min", 0))
    hi = float(specs.get("max", 0))
    return lo >= 0 and hi >= 1000


def _random_value(data_type: str, specs: dict) -> object:
    """根据 dataType 和 specs 生成符合规范的随机值（快照量）。"""
    if data_type == "int64":
        lo = int(specs["min"])
        hi = int(specs["max"])
        step = int(specs.get("step", 1))
        val = random.randint(lo, hi)
        if step > 1:
            val = lo + ((val - lo) // step) * step
        return val

    if data_type == "double":
        lo = float(specs["min"])
        hi = float(specs["max"])
        step = float(specs.get("step", 0.001))
        val = random.uniform(lo, hi)
        if step > 0:
            val = round(lo + round((val - lo) / step) * step, 6)
        return val

    if data_type == "bool":
        return random.choice([True, False])

    if data_type == "enum":
        keys = list(specs.keys())
        key = random.choice(keys)
        try:
            return int(key)
        except ValueError:
            return key

    return None


def _random_cumulative(data_type: str, specs: dict, current: float, step_hint: float) -> float:
    """累计量：在当前值基础上加一个小增量，不超过 max。"""
    lo = float(specs["min"])
    hi = float(specs["max"])
    step = float(specs.get("step", 1))

    if step_hint > 0:
        delta = random.uniform(step_hint * 0.2, step_hint)
    else:
        # 没配 hint，按 step 估计一个小增量
        delta = random.uniform(step, step * 100)

    new_val = current + delta
    if new_val > hi:
        new_val = hi

    if data_type == "int64":
        return int(new_val)
    return round(new_val, 6)


# ====== 设备状态：维护累计量的上次值 ======

# key = (device_type, device_id), value = {identifier: last_value}
_DEVICE_STATE: dict[tuple[str, str], dict[str, float]] = {}


def _get_or_init_state(device_type: str, device_id: str) -> dict[str, float]:
    """获取或初始化设备的累计量状态。

    初始化时从 specs 范围的 30%~60% 取一个起始值，避免总是从 0 开始。
    """
    key = (device_type, device_id)
    if key in _DEVICE_STATE:
        return _DEVICE_STATE[key]

    model = _load_device_model(device_type)
    state: dict[str, float] = {}

    for prop in model["properties"]:
        identifier = prop["identifier"]
        if identifier in _TIMESTAMP_FIELDS:
            continue

        specs = prop["dataType"].get("specs", {})
        data_type = prop["dataType"]["type"]

        if identifier in _CUMULATIVE_FIELDS or _looks_cumulative(specs):
            lo = float(specs.get("min", 0))
            hi = float(specs.get("max", 1000))
            # 从 30%~60% 范围取初值
            start_pct = random.uniform(0.3, 0.6)
            init_val = lo + (hi - lo) * start_pct
            step = float(specs.get("step", 1))
            if data_type == "int64":
                state[identifier] = int(init_val)
            else:
                state[identifier] = round(init_val, 6)

    _DEVICE_STATE[key] = state
    return state


def _build_data_from_model(device_type: str, device_id: str) -> dict:
    """按物模型定义生成一条上报数据，累计量单调递增。"""
    model = _load_device_model(device_type)
    ts = _now_ts()
    state = _get_or_init_state(device_type, device_id)
    data: dict[str, object] = {}

    for prop in model["properties"]:
        identifier = prop["identifier"]
        data_type = prop["dataType"]["type"]
        specs = prop["dataType"].get("specs", {})

        if identifier in _TIMESTAMP_FIELDS:
            data[identifier] = ts
            continue

        # 累计量：在 state 基础上递增
        if identifier in state:
            step_hint = _CUMULATIVE_FIELDS.get(identifier, (0, 0))[1]
            new_val = _random_cumulative(data_type, specs, state[identifier], step_hint)
            state[identifier] = new_val
            data[identifier] = new_val
            continue

        # 快照量 / bool / enum：正常随机
        val = _random_value(data_type, specs)
        if val is not None:
            data[identifier] = val

    # 日最大流量：取 max(dayMaxFlow, instFlow)
    if "dayMaxFlow" in data and "instFlow" in data:
        inst = float(data["instFlow"])
        data["dayMaxFlow"] = max(float(data["dayMaxFlow"]), inst)
        data["dayMaxFlowTime"] = ts

    return data


# ====== 设备上报策略 ======

def device_fixed(count: int, device_id: str, device_type: str) -> dict:
    """固定值：从 JSON 模板加载，注入实时时间戳和设备标识。"""
    template = _load_device_template(device_type)
    ts = _now_ts()

    # 注入动态字段
    template["ts"] = ts
    template["SN"] = device_id
    if "data" in template and "recTime" in template["data"]:
        template["data"]["recTime"] = ts
    if "data" in template and "lastReadTime" in template["data"]:
        template["data"]["lastReadTime"] = ts

    return template


def device_random(count: int, device_id: str, device_type: str) -> dict:
    """随机值：严格按物模型 specs 生成，累计量单调递增，快照量实时波动。

    - 累计量（totalFlow, kWhImp, 累计运行次数…）在 state 基础上递增，不倒退
    - 快照量（instFlow, 电压电流, 楼层位置…）每条在 specs 范围内随机
    - bool/enum 告警位每条随机
    - status / cmd / group 从 payloads/ 模板取，不在此硬编码
    """
    template = _load_device_template(device_type)
    ts = _now_ts()

    data = _build_data_from_model(device_type, device_id)

    return {
        "cmd": template.get("cmd", "SnapshotData"),
        "ts": ts,
        "SN": device_id,
        "group": template.get("group", 1),
        "status": template.get("status", "online"),
        "data": data,
    }


# ====== 策略注册表（扩展点）======
# 加新策略：定义上面函数 → 在这里加一行

DEVICE_STRATEGIES = {
    "fixed": device_fixed,
    "random": device_random,         # 严格按物模型 specs 随机
    # "increment": device_increment,   # 每条温度 +2°C，测超阈值告警
    # "sine":       device_sine,        # 正弦波动，测上下限告警
}


def build_device_payload(count: int, mode: str, device_id: str, device_type: str = "water_meter") -> dict:
    """按 mode 分发到对应策略函数。"""
    if mode not in DEVICE_STRATEGIES:
        raise ValueError(
            f"未知 device mode: {mode!r}, 可用: {list(DEVICE_STRATEGIES)}"
        )
    return DEVICE_STRATEGIES[mode](count, device_id, device_type)
