# MQTT 设备消息模拟模块

模拟水表、电表、电梯等物联网设备，通过 MQTT 协议向业务平台上报快照数据与告警事件，用于联调、演示和平台侧接收逻辑的验证。

纯 Python 实现，基于 [paho-mqtt](https://github.com/eclipse/paho.mqtt.python) 2.x，数据落本地 JSON 文件，无需数据库。

---

## 目录结构

```
scripts/mqtt/
├── send_payload_once.py     # 单发脚本：发送一条消息后退出
├── send_payload_loop.py     # 循环脚本：按间隔持续上报，支持累计量递增/状态翻转
├── generators/
│   └── payload_builder.py   # payload 生成器（策略模式）：按物模型自动生成数据
├── payloads/                # 固定 payload 模板（JSON）
│   ├── water_meter_report.json
│   ├── electric_meter_report.json
│   ├── elevator_report.json
│   └── elevator_alarm.json
└── models/                  # 设备物模型定义（字段类型/范围/步长）
    ├── model_water_meter.json
    ├── model_eletric_meter.json
    └── model_elevator.json
```

底层连接能力在仓库根目录的 [common/mqtt_publisher.py](../../common/mqtt_publisher.py)，本模块只负责"发什么、怎么发"。

---

## 环境准备

### 1. 安装依赖

需要 Python 3.10+，在**仓库根目录**执行：

```bash
pip install -e ".[mqtt,core]"
```

其中：
- `mqtt` extra 安装 `paho-mqtt>=2.1`
- `core` extra 安装配置读取所需的 `pydantic-settings`、`python-dotenv`

只装最小依赖也可以：

```bash
pip install "paho-mqtt>=2.1" "pydantic-settings>=2.0" python-dotenv
```

### 2. 配置 broker

在仓库根目录复制 `.env.example` 为 `.env`，按需修改 MQTT 段：

```ini
# ---- MQTT 配置 ----
MQTT_BROKER_HOST=broker.emqx.io   # broker 地址，默认用 EMQX 公共测试服务器
MQTT_BROKER_PORT=1883
MQTT_BROKER_USERNAME=             # 留空 = 匿名访问
MQTT_BROKER_PASSWORD=
MQTT_CLIENT_ID=automation-suite-01  # 客户端 ID，多开时必须改，否则互相踢线
MQTT_KEEPALIVE=60
MQTT_DEFAULT_QOS=1                # 建议保持 1，原因见"常见问题"
MQTT_CONNECT_TIMEOUT=10
```

配置由 `common.mqtt_publisher.MqttConfig` 自动读取，前缀固定为 `MQTT_`。

---

## 快速开始

> ⚠️ **所有脚本都必须在仓库根目录运行**（脚本内 `from common.mqtt_publisher import ...` 依赖根目录在 Python 路径中）。

### 发送一条消息

适合点测、验证平台能不能收到：

```bash
python scripts/mqtt/send_payload_once.py
```

修改 [send_payload_once.py](send_payload_once.py) 头部两个参数即可切换设备：

```python
DEVICE_ID = "342401003"
DEVICE_TYPE = "elevator_report"
```

脚本会自动：
1. 读取 `payloads/{DEVICE_TYPE}.json` 模板
2. 把 `SN` 替换为 `DEVICE_ID`
3. 把 `ts` 及 data 内的时间字段刷新为当前时间
4. 发布到对应 topic，并在终端打印 payload

### 循环上报

模拟设备持续在线、数据不断变化：

```bash
python scripts/mqtt/send_payload_loop.py
```

`Ctrl + C` 停止。终端会滚动打印每条消息：

```
[000] topic=WATER/METER/342401030/upload status=online cum=52.37 ts=1789865170
[001] topic=WATER/METER/342401030/upload status=online cum=98.12 ts=1789865172
```

---

## 设备类型与 Topic 对照

| `DEVICE_TYPE`            | 消息类型     | Topic 模式                          | payload 模板                   |
| ------------------------ | ------------ | ----------------------------------- | ------------------------------ |
| `water_meter_report`     | 快照 SnapshotData  | `WATER/METER/{id}/upload`           | `water_meter_report.json`      |
| `electric_meter_report`  | 快照 SnapshotData  | `CET/PMC-350/{id}/upload`           | `electric_meter_report.json`   |
| `elevator_report`        | 快照 SnapshotData  | `ELEVATOR/PROPERTY/{id}/upload`     | `elevator_report.json`         |
| `elevator_alarm`         | 事件 EventData     | `ELEVATOR/EVENT/{id}/upload`        | `elevator_alarm.json`          |

> SN 类型注意：电表模板的 `SN` 是**整数**，其余是字符串。循环脚本会自动识别模板类型做转换，不会把 `342401020` 发成 `"342401020"`。

### 消息结构

快照类（`SnapshotData`）：

```json
{
  "cmd": "SnapshotData",
  "ts": 1789629900,
  "SN": "342401030",
  "group": 1,
  "status": "online",
  "data": { "recTime": 1789629900, "totalFlow": 2099.08, "instFlow": 3.59 }
}
```

事件类（`EventData`，电梯告警）：

```json
{
  "cmd": "EventData",
  "ts": 1789635300,
  "SN": "342401003",
  "group": 1,
  "data": {
    "fault_code": "E03",
    "fault_name": "编码器信号异常",
    "fault_level": 2,
    "fault_time": 1789635300,
    "fault_floor": 4,
    "fault_desc": "编码器线缆断线"
  }
}
```

---

## 循环脚本参数详解

[send_payload_loop.py](send_payload_loop.py) 头部参数区：

| 参数 | 默认值 | 说明 |
| --- | --- | --- |
| `DEVICE_ID` | `"342401030"` | 设备编号，会注入 topic 和 payload 的 `SN` |
| `DEVICE_TYPE` | `"water_meter_report"` | 设备类型，决定 topic 和模板文件 |
| `INTERVAL_SECONDS` | `2` | 每条消息间隔秒数 |
| `MAX_COUNT` | `100` | 发送条数；设为 `None` 则无限循环到 `Ctrl+C` |
| `STATUS_MODE` | `1` | 在线状态：`0`=恒 offline，`1`=恒 online，`2`=每条随机 online/offline |
| `CUMULATIVE_INITIAL` | `0` | 累计量初始值 |
| `CUMULATIVE_STEP_MIN` | `3` | 每条累计量最小增量 |
| `CUMULATIVE_STEP_MAX` | `100` | 每条累计量最大增量 |

每条消息自动处理：

- **时间戳**：顶层 `ts` 实时刷新；data 内的 `recTime`、`lastReadTime`、`dayMaxFlowTime`、`fault_time` 同步刷新
- **累计量递增**：电表递增 `kWhImp`；水表共用同一累计值递增 `totalFlow`、`flowPos`、`flowNet`（字段映射见脚本内 `_CUMULATIVE_FIELDS`）
- **SN 注入**：按模板原始类型自动转 int 或保持字符串
- **状态字段**：按 `STATUS_MODE` 写入 `status`

### 特殊用法：回放固定时间戳

脚本内置了 2026 年 120 个时间戳（每月 10 个，见 `_FIXED_TS`）。需要让平台收到"历史时间"的数据时，把这一行取消注释、实时时间那行注释掉即可：

```python
payload["ts"] = int(time.time())              # 默认：实时
# payload["ts"] = _FIXED_TS[count % len(_FIXED_TS)]  # 按顺序循环固定时间
```

### 定制钩子 `_customize`

需要更复杂的数据变化（告警位翻转、瞬时流量越限等）时，在脚本的 `_customize(data, count)` 函数里写逻辑，它会在每条消息发布前被原地调用：

```python
def _customize(data: dict, count: int) -> None:
    if count % 20 == 0:
        data["lowBattAlarm"] = True   # 每 20 条触发一次低电量告警
```

---

## Payload 生成器（策略模式）

[generators/payload_builder.py](generators/payload_builder.py) 提供不依赖固定模板的程序化生成能力，目前是库形式，可在新脚本中 import 使用。

### 两种内置策略

| 策略 | 函数 | 行为 |
| --- | --- | --- |
| `fixed` | `device_fixed` | 读 `payloads/` 模板，只刷新时间戳和 SN（等价于单发脚本逻辑） |
| `random` | `device_random` | 严格按 `models/` 物模型 specs 生成：**累计量单调递增、快照量每条随机、bool/enum 随机翻转** |

`random` 策略的数据语义：

- **累计量**（`totalFlow`、`kWhImp`、`accumulativeRunNum` 等）：进程内按 `(设备类型, 设备ID)` 维护状态，只增不减；初值取物模型量程的 30%~60%，模拟已投运设备
- **快照量**（`instFlow`、电压电流、轿厢位置等）：每条在 specs 的 min/max 内随机，遵守 step
- **时间戳字段**（`recTime`、`lastReadTime`、`dayMaxFlowTime`）：统一取当前时间
- 日最大流量自动取 `max(dayMaxFlow, instFlow)`

### 在代码中使用

```python
from scripts.mqtt.generators.payload_builder import build_device_payload
from common.mqtt_publisher import MqttPublisher

payload = build_device_payload(
    count=0,
    mode="random",                 # fixed / random
    device_id="342401030",
    device_type="water_meter",     # water_meter / electric_meter / elevator
)

with MqttPublisher() as pub:
    pub.publish("WATER/METER/342401030/upload", payload)
```

### 扩展新策略

1. 在 `payload_builder.py` 中定义函数，签名固定为 `(count, device_id, device_type) -> dict`
2. 在文件末尾 `DEVICE_STRATEGIES` 字典注册一行
3. 调用时 `mode` 传注册名即可

```python
def device_sine(count: int, device_id: str, device_type: str) -> dict:
    ...

DEVICE_STRATEGIES = {
    "fixed": device_fixed,
    "random": device_random,
    "sine": device_sine,   # 新增
}
```

文件中预留了 `increment`（线性递增，测超阈值告警）、`sine`（正弦波动，测上下限告警）两个注释位，可按需实现。

---

## 新增设备类型

以新增"燃气表"为例：

1. **加 payload 模板**：`payloads/gas_meter_report.json`，字段结构对齐快照格式
2. **加物模型**（可选，用 random 策略时需要）：`models/model_gas_meter.json`
3. **在脚本 `_TOPICS` 加映射**：

   ```python
   "gas_meter_report": f"GAS/METER/{DEVICE_ID}/upload",
   ```

   单发和循环两个脚本都要改
4. 若用生成器，再在 `payload_builder.py` 的 `DEVICE_TYPE_MAP` 和 `_MODEL_FILE_MAP` 各加一行
5. 把 `DEVICE_TYPE` 改为新类型，运行

---

## 常见问题

### 1. 平台收不到消息 / 偶发丢消息

检查 `.env` 的 `MQTT_DEFAULT_QOS`。QoS=0 时消息发出后客户端立即退出，broker 来不及转发就会丢；`MqttPublisher.publish()` 内部对 QoS≥1 会 `wait_for_publish()` 等 broker 的 PUBACK。**保持 `MQTT_DEFAULT_QOS=1`**。

### 2. 多开脚本互相掉线

`MQTT_CLIENT_ID` 相同的两个连接会被 broker 互踢。每开一个实例改一个唯一 ID。

### 3. `ModuleNotFoundError: No module named 'common'`

运行目录不对。切到仓库根目录再执行 `python scripts/mqtt/xxx.py`，不要在 `scripts/mqtt/` 目录里直接跑。

### 4. 电表 SN 类型告警

电表平台一般要求 SN 为整数。循环脚本已按模板类型自动转换；自己改脚本时注意不要给电表传字符串 SN。

### 5. 连不上公共 broker

`broker.emqx.io` 是 EMQX 提供的公共测试服务，不保证可用性。联调环境建议换成自建 broker 地址，内网部署时同时确认 1883 端口和防火墙。

---

## 相关文件

- 底层发布器：[common/mqtt_publisher.py](../../common/mqtt_publisher.py)（懒连接、上下文管理、dict 自动转 JSON、批量发布）
- 环境变量样例：[.env.example](../../.env.example)
- MQTT 自定义异常：[common/exceptions.py](../../common/exceptions.py)
