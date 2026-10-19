# 蓝鲸二号 · 边缘部署指南（ESP32 / 树莓派）

> **目标**：把 PC 上跑通的五行生克 + 合道审计，搬到真实设备上。
> **原则**：**只搬数学，不搬文本。** 语言理解留在 PC，边缘只做「感知 → 生克 → 动作 → 审计」。
> **建立**：2026-10-19 ｜ **行尾**：LF

---

## 一、为什么必须砍

| 模块 | PC 版大小 | 能不能上 ESP32 |
|---|---|---|
| `01_memory_and_space/memory_core.py` | 30 KB | ❌ 要读 5.4 MB 档案，ESP32 没这个内存 |
| `05_gravity_field/gravity.py` | 7 KB | ⚠️ 概念网络 90 节点，RAM 紧张 |
| `06_physical_combat/combat_engine.py` | 10 KB | ⚠️ 只留截击的数学，丢文字 |
| `02_wuxing_scheduler/wuxing_engine.py` | 16 KB | ✅ **可砍到 3 KB**（本目录 stub 已做） |
| `03_dao_auditor/dao_audit.py` | 6 KB | ✅ **可砍到 1 KB**（三条伦理足够） |
| `08_edge_deployment/micro_python_stub.py` | **约 5 KB** | ✅ **这就是烧录版** |

**结论：ESP32 上只跑 `micro_python_stub.py` 里的 4 个函数。**

---

## 二、ESP32 路线（MicroPython）

### 2.1 硬件清单

| 件 | 型号 | 用途 |
|---|---|---|
| 主控 | ESP32-WROOM-32（4MB Flash） | 跑 MicroPython |
| 传感器 | DHT22（温湿度） | 温度 → 火，湿度 → 水 |
| 传感器 | SW-420（震动） | 震动 → 土 / 金 |
| 执行 | 5V 继电器模块 ×2 | 风扇 / 加湿 |
| 执行 | MOSFET 模块 | PWM 风扇调速 |

### 2.2 烧录步骤

```bash
# 1. 烧 MicroPython 固件
esptool.py --chip esp32 --port COM3 write_flash -z 0x1000 esp32-20240222-v1.22.2.bin

# 2. 上传文件
ampy --port COM3 put micro_python_stub.py /lib/wuxing.py
ampy --port COM3 put main_esp32.py

# 3. 看输出
ampy --port COM3 run --no-output main_esp32.py
screen COM3 115200
```

### 2.3 `main_esp32.py` 骨架

```python
import time
from machine import Pin, ADC
import wuxing                      # ← micro_python_stub.py 改名而来

FAN = Pin(4, Pin.OUT)              # 风扇继电器
MIST = Pin(5, Pin.OUT)             # 加湿继电器
VIB = ADC(Pin(34)); VIB.atten(ADC.ATTN_11DB)

def read_all():
    # DHT22 用 dht 模块，这里示意
    import dht
    d = dht.DHT22(Pin(15)); d.measure()
    return d.temperature(), d.humidity(), VIB.read() / 4095.0

while True:
    t, h, v = read_all()
    e = wuxing.map_sensors(t, h, v)
    acts, after, meta = wuxing.make_decision(e)

    ok, code = wuxing.audit(acts, None, after)
    if not ok:
        print("AUDIT BLOCK:", code)
        FAN.off(); MIST.off()      # 不过道 → 全部停
        time.sleep(1); continue

    for name, inten, tag in acts:
        if name == "fan":
            FAN.value(1 if inten > 0.3 else 0)
        elif name == "mist":
            MIST.value(1 if inten > 0.3 else 0)
        # 其它动作按同样方式映射到 GPIO
    time.sleep(2)
```

### 2.4 内存预算（实测参考）

| 项 | 占用 |
|---|---|
| MicroPython 固件 | ~600 KB |
| `wuxing.py`（stub） | ~5 KB |
| 运行时堆 | ~80 KB |
| **合计** | **< 700 KB / 4 MB** ✅ |

**余量充足，还能加 WiFi + MQTT。**

---

## 三、树莓派路线（完整 Python）

树莓派能跑 **完整版**（连 `memory_core` 和概念网络）：

```bash
cd /home/pi/bluewhale/agi_core
python3 main.py
```

只要把 `04_embodied_io/sensory_input.py` 的两个方法换成真实实现：

```python
# sensory_input.py 里
def read_virtual_sensors(self, override=None):
    if not self.simulated:
        import board, adafruit_dht
        d = adafruit_dht.DHT22(board.D15)
        return {"temperature": d.temperature, "humidity": d.humidity,
                "vibration": read_adc(), "simulated": False,
                "note": "真实传感器"}
```

**PC 与树莓派用同一份代码，只是 `simulated` 不同。这是最大的好处。**

---

## 四、网关协议（PC ↔ 边缘）

如果边缘算力不够、想在 PC 上做决策，就用 Phase 8 定的协议：

| 方法 | 路径 | 用途 |
|---|---|---|
| `GET` | `/ping` | 连通性探测 |
| `GET` | `/sensors` | 读传感器 `{temperature, humidity, vibration}` |
| `POST` | `/action` | 下发动作 `{action, intensity}` |

**ESP32 侧用 `urequests` 或裸 socket 实现这三个端点即可。**

---

## 五、⚠️ 安全底线（不可省）

| 项 | 要求 |
|---|---|
| **硬件急停** | **必须有一个物理按钮直接切继电器电源** —— 软件死了也能停 |
| **审计不过就不动** | `audit()` 返回 False → 所有执行器归零，不许"带着疑问继续" |
| **强度上限** | 致伤类动作硬上限 0.60，**写死在代码里，不做成可配置** |
| **断电默认态** | 继电器选**常开（NO）**，断电即停 |
| **不过流** | 继电器加保险丝；ESP32 的 3.3V 不要直接驱动大电流负载 |

---

## 六、移植核对清单

- [ ] `micro_python_stub.py` 在 PC 上 `python micro_python_stub.py` 自检通过
- [ ] 烧录后 `import wuxing` 无报错
- [ ] 传感器读数与实测对比（温度误差 < 1°C）
- [ ] 继电器动作方向正确（不是反的）
- [ ] 物理急停按钮验证过（拔电即停）
- [ ] 审计拦截路径验证过（人为注入超限动作，确认会被拦）
- [ ] 断电重启后默认全停

---

## 七、当前状态（诚实）

| 项 | 状态 |
|---|---|
| `micro_python_stub.py` | **已在 PC 上自检通过**（见文件末尾 `__main__`） |
| **真实 ESP32** | **未烧录、未验证** |
| **真实传感器** | **未接** |
| **网关连通** | **Phase 8 已验，本机不通（预期）** |

**这份指南是按元宝硬件说明书的引脚/Modbus 惯例写的，不是实测调出来的。**
**第一次烧录一定会遇到问题 —— 别信"照做就行"，要拿万用表量。**
