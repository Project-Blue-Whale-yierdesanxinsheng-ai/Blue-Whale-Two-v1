# -*- coding: utf-8 -*-
"""04 · 具身接口（传感器）。

核心哲学（三的原话）：
    距离 = 我在哪和我和其他物资的动静态关系

两种模式：
    1. **模拟模式**（use_network=False）—— 返回固定场景值，标 simulated=True
    2. **网络模式**（use_network=True） —— 从网关读 JSON

铁律：
    **连不上就降级，绝不崩、绝不假装读到了真数据。**
    降级时打印「硬件离线，切换回模拟数据」，并返回**正常值**（五行都 0.5）。
"""

import json
import urllib.error
import urllib.request

# 默认网关（三给的示例地址；真机改这里或构造时传参）
GATEWAY = "http://192.168.1.100/api"
# 超时（秒）。1.0 是折中：本地测试不卡，局域网真机也够
TIMEOUT = 1.0

# 降级时返回的"正常值"：五行皆 0.5，系统会判定"无需动作"
NORMAL_READING = {
    "temperature": 25.0,   # → 火 0.5
    "humidity": 50.0,      # → 水 0.5
    "vibration": 0.02,     # → 土 0.5 / 金 0.5
}

# 模拟模式下的"故障场景"（故意设成过热缺水，好让生克跑起来）
SCENARIO_READING = {
    "temperature": 85.0,
    "humidity": 20.0,
    "vibration": 0.10,
}


class SensoryInput:
    """传感器矩阵入口。"""

    def __init__(self, use_network=False, gateway=GATEWAY, timeout=TIMEOUT):
        self.use_network = bool(use_network)
        self.gateway = gateway.rstrip("/")
        self.timeout = float(timeout)
        self.online = None          # None=未探测 / True / False
        self.degraded = False        # 是否已从网络降级到模拟
        self.last_error = ""

    # ────────── 连通性探测 ──────────
    def probe(self):
        """探测网关是否可达。返回 (ok, 说明)。"""
        if not self.use_network:
            self.online = False
            return False, "网络模式未启用（模拟模式）"
        url = self.gateway + "/ping"
        try:
            req = urllib.request.Request(url, method="GET")
            with urllib.request.urlopen(req, timeout=self.timeout) as r:
                self.online = 200 <= getattr(r, "status", 0) < 300
                return self.online, "网关可达 HTTP %s" % getattr(r, "status", "?")
        except Exception as e:
            self.online = False
            self.last_error = "%s: %s" % (type(e).__name__, e)
            return False, "网关不可达（%s）" % self.last_error

    # ────────── 读环境 ──────────
    def read_virtual_sensors(self, override=None):
        """读取环境数据。

        网络模式下先试网络；失败则**降级**为模拟（返回正常值，不是故障场景）。
        override 可以覆盖任意一项，方便做故障演练。
        """
        if self.use_network and not self.degraded:
            ok, data, why = self._read_network()
            if ok:
                out = dict(data)
                out.setdefault("simulated", False)
                out.setdefault("note", "网络传感器（来自 %s）" % self.gateway)
                if override:
                    out.update(override)
                return out
            # ── 降级 ──
            self.degraded = True
            print("     ⚠ 硬件离线，切换回模拟数据（原因：%s）" % why)

        base = NORMAL_READING if self.degraded else SCENARIO_READING
        out = dict(base)
        out["simulated"] = True
        out["note"] = ("虚拟传感器（已从网络降级；不是真硬件）"
                       if self.degraded else
                       "虚拟传感器（Phase 1 无实体，不是真硬件）")
        if override:
            out.update(override)
        return out

    # ────────── 网络读取 ──────────
    def _read_network(self):
        """从网关 GET 传感器 JSON。返回 (ok, data, 说明)。"""
        url = self.gateway + "/sensors"
        try:
            req = urllib.request.Request(url, method="GET")
            with urllib.request.urlopen(req, timeout=self.timeout) as r:
                body = r.read(4096).decode("utf-8", "replace")
                if not (200 <= getattr(r, "status", 0) < 300):
                    return False, {}, "HTTP %s" % getattr(r, "status", "?")
                data = json.loads(body)
                if not isinstance(data, dict):
                    return False, {}, "返回不是 JSON 对象"
                # 至少要有一个已知字段
                if not any(k in data for k in NORMAL_READING):
                    return False, {}, "返回缺少 temperature/humidity/vibration"
                self.online = True
                return True, data, "ok"
        except json.JSONDecodeError as e:
            self.last_error = "JSONDecodeError: %s" % e
            self.online = False
            return False, {}, self.last_error
        except urllib.error.HTTPError as e:
            self.last_error = "HTTPError %s %s" % (e.code, e.reason)
            self.online = False
            return False, {}, self.last_error
        except urllib.error.URLError as e:
            self.last_error = "URLError %s" % (e.reason,)
            self.online = False
            return False, {}, self.last_error
        except Exception as e:
            self.last_error = "%s: %s" % (type(e).__name__, e)
            self.online = False
            return False, {}, self.last_error

    # ────────── 距离（保持原样） ──────────
    def get_physical_distance(self):
        """返回物理距离信息（静态 + 动态）。"""
        if self.use_network and not self.degraded:
            ok, data, why = self._read_network()
            if ok and data.get("distance_m") is not None:
                return {
                    "simulated": False,
                    "is_silicon_side": False,
                    "nearest_landmark": data.get("landmark", "网关上报位置"),
                    "static_distance_m": float(data["distance_m"]),
                    "dynamic_delta_m": float(data.get("delta_m", 0.0)),
                    "sensors": data,
                    "note": "网络距离（来自 %s）" % self.gateway,
                }
            if not self.degraded:
                self.degraded = True
                print("     ⚠ 硬件离线，切换回模拟数据（原因：%s）" % why)

        return {
            "simulated": True,
            "is_silicon_side": False,
            "nearest_landmark": "E:\\bluewhale（本地硬盘）",
            "static_distance_m": 0.00,
            "dynamic_delta_m": 0.00,
            "sensors": {
                "温度_C": 37.0,
                "湿度_pct": None,
                "电流_A": None,
            },
            "note": "Phase 1 无实体：距离恒为 0，因为此刻只有硬盘和屏幕",
        }
