# -*- coding: utf-8 -*-
"""04 · 执行器（Actuator）。

核心哲学（三的原话）：
    五行生克 → 落到物理动作

两种模式：
    1. **模拟模式**（use_network=False）—— 只打印，不驱动任何设备
    2. **网络模式**（use_network=True） —— 向本地网关发 JSON

铁律：
    **发送失败必须捕获异常并报警，绝不假装成功。**
    返回体里 `ok=False` ＋ `error` 字段就是凭据。
"""

import json
import urllib.error
import urllib.request

# 默认网关（三给的示例地址；真机改这里或构造时传参）
GATEWAY = "http://192.168.1.100/api"
# 超时（秒）。1.0 是折中：本地测试不卡，局域网真机也够
TIMEOUT = 1.0


class Actuator:
    """执行器：把五行决策落成物理动作。"""

    def __init__(self, use_network=False, gateway=GATEWAY, timeout=TIMEOUT):
        self.use_network = bool(use_network)
        self.gateway = gateway.rstrip("/")
        self.timeout = float(timeout)
        self.online = None          # None=未探测 / True / False
        self.history = []
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

    # ────────── 执行动作 ──────────
    def execute_action(self, action_name, intensity):
        """执行一个动作。

        action_name: 动作名（如「开启散热风扇」）
        intensity:   强度 0–1
        """
        inten = max(0.0, min(1.0, float(intensity)))

        if self.use_network:
            ok, detail = self._send_network(action_name, inten)
        else:
            ok, detail = self._dispatch_simulated(action_name, inten)

        rec = {
            "action": action_name,
            "intensity": round(inten, 3),
            "ok": ok,
            "detail": detail,
            "simulated": not (self.use_network and ok),
        }
        if not ok:
            rec["error"] = self.last_error or detail
        self.history.append(rec)

        if ok:
            print("       ⚙ 执行器动作 → %s（强度 %.0f%%）%s"
                  % (action_name, inten * 100,
                     "" if self.use_network else "  [模拟，未驱动真硬件]"))
            print("         %s" % detail)
        else:
            print("       🚨 执行器报警 → %s 发送失败" % action_name)
            print("         原因：%s" % (rec.get("error") or detail))
            print("         **未执行，也未假装成功。**")
        return rec

    # ────────── 网络下发 ──────────
    def _send_network(self, action_name, intensity):
        """向网关 POST 一条 JSON 动作。失败必抛 → 被捕获 → 报警。"""
        if self.online is False:
            self.last_error = "网关未连通（probe 已失败）"
            return False, "网关未连通，动作未发送"

        url = self.gateway + "/action"
        payload = json.dumps({
            "action": action_name,
            "intensity": round(intensity, 3),
            "ts": None,
        }, ensure_ascii=False).encode("utf-8")

        try:
            req = urllib.request.Request(
                url, data=payload, method="POST",
                headers={"Content-Type": "application/json; charset=utf-8"})
            with urllib.request.urlopen(req, timeout=self.timeout) as r:
                body = r.read(200).decode("utf-8", "replace")
                if not (200 <= getattr(r, "status", 0) < 300):
                    self.last_error = "HTTP %s" % getattr(r, "status", "?")
                    return False, "网关返回非 2xx：%s" % self.last_error
                return True, "已下发到 %s ｜ 回执 %s" % (url, body[:80] or "（空）")
        except urllib.error.HTTPError as e:
            self.last_error = "HTTPError %s %s" % (e.code, e.reason)
            return False, self.last_error
        except urllib.error.URLError as e:
            self.last_error = "URLError %s" % (e.reason,)
            return False, self.last_error
        except Exception as e:
            self.last_error = "%s: %s" % (type(e).__name__, e)
            return False, self.last_error

    # ────────── 模拟下发 ──────────
    def _dispatch_simulated(self, action_name, intensity):
        """模拟：只描述「如果真有硬件，这一步会做什么」。"""
        DESC = {
            "开启散热风扇": "PWM 占空比拉到 %.0f%%，风扇启动" % (intensity * 100),
            "启动雾化加湿": "加湿模块通电，雾化 %.0f%% 功率" % (intensity * 100),
            "升温退火": "加热片通电，目标温度上调 %.0f%%" % (intensity * 100),
            "抑制过度生长": "限流阀关小，输出压到 %.0f%%" % (intensity * 100),
            "松土减载": "卸荷机构启动，负载下调 %.0f%%" % (intensity * 100),
            "启动排水泵": "排水泵启动，流量 %.0f%%" % (intensity * 100),
            "通风助燃": "风门打开 %.0f%%" % (intensity * 100),
            "加固结构": "支撑件锁紧，预紧力 %.0f%%" % (intensity * 100),
            "补液灌溉": "补液阀打开 %.0f%%" % (intensity * 100),
            "升温养护": "保温层通电，目标上调 %.0f%%" % (intensity * 100),
            # ── 支点动作（轻启动，用来放大下游）──
            "启动冷凝器": "冷凝器轻载启动 %.0f%%，开始把空气中的水分析出" % (intensity * 100),
            "开启补水阀": "补水阀微开 %.0f%%，水路开始回压" % (intensity * 100),
            "启动引风机": "引风机低速运转 %.0f%%，气流开始定向" % (intensity * 100),
            "点火预热": "预热丝通电 %.0f%%，为点火创造条件" % (intensity * 100),
            "压实基础": "压实机构轻压 %.0f%%，地基开始承力" % (intensity * 100),
        }
        return True, DESC.get(action_name, "通用执行：%s @ %.0f%%"
                              % (action_name, intensity * 100))

    # ────────── 复合动作：先设支点，再出倍力 ──────────
    def execute_composite(self, leverage):
        """执行一次「支点 + 倍力」的复合动作。

        leverage 来自 WuXingEngine.find_pivot_and_leverage()，包含：
            pivot_action {name, intensity}
            main_action  {name, intensity}
            chain / k / resistance / force
        """
        piv = leverage["pivot_action"]
        main = leverage["main_action"]

        print("       ┌─ 力学复合动作 ｜ 链条 %s ─" % leverage["chain"])
        print("       │  原始阻力 R = %.3f ｜ 放大系数 k = %.2f" % (
            leverage["resistance"], leverage["k"]))
        print("       │  实际输出 F = R / k = %.3f（省力 %.1f%%）"
              % (leverage["force"], leverage["saving_pct"]))
        print("       │")

        print("       │  ① 先设支点：%s（轻启动，强度 %.0f%%）"
              % (piv["name"], piv["intensity"] * 100))
        r1 = self.execute_action(piv["name"], piv["intensity"])

        print("       │  ② 再出倍力：%s（强度 %.0f%%，被 k=%.2f 放大）"
              % (main["name"], main["intensity"] * 100, leverage["k"]))
        r2 = self.execute_action(main["name"], main["intensity"])

        ok = bool(r1["ok"] and r2["ok"])
        print("       └─ 复合动作 %s" % ("完成" if ok else "**有环节失败，见上方报警**"))
        return {
            "ok": ok,
            "chain": leverage["chain"],
            "pivot": r1,
            "main": r2,
            "k": leverage["k"],
            "force": leverage["force"],
            "saving_pct": leverage["saving_pct"],
        }

    # ────────── 台账 ──────────
    def dump_history(self):
        if not self.history:
            print("       （尚无动作）")
            return
        for i, r in enumerate(self.history, 1):
            flag = "成功" if r["ok"] else "**失败**"
            mode = "真实" if (r["simulated"] is False) else "模拟"
            print("       %d. %-12s %.0f%% ｜ %s ｜ %s"
                  % (i, r["action"], r["intensity"] * 100, flag, mode))
