# -*- coding: utf-8 -*-
"""02 · 五行调度器。

核心哲学（三的原话）：
    五行：生克乘侮的加减乘除调度算法

把五种"力"当账本：
    相生 = 加（把能量递给下一个）
    相克 = 减（把能量收回来）
    相乘 = 乘（过度克制，放大伤害）
    相侮 = 除（反向欺侮，秩序倒转）
"""


class WuXingEngine:
    """五行生克乘侮调度器。"""

    # 相生：木→火→土→金→水→木
    SHENG = {"木": "火", "火": "土", "土": "金", "金": "水", "水": "木"}
    # 相克：木克土，土克水，水克火，火克金，金克木
    KE = {"木": "土", "土": "水", "水": "火", "火": "金", "金": "木"}

    def __init__(self):
        # 初始五行配比（0-1），代表资源/算力/注意力
        self.state = {"木": 0.5, "火": 0.5, "土": 0.5, "金": 0.5, "水": 0.5}

    def _clamp(self, v):
        return max(0.0, min(1.0, v))

    def calculate_energy_flow(self, context, demand=None):
        """按条件场算一次能量流转。

        demand 可以指定要加哪个、要减哪个（默认按最弱项补）。
        """
        st = dict(self.state)
        demand = demand or {}

        # 找一个最弱的元素来补（补不足，不补有余）
        weakest = min(st, key=lambda k: st[k])
        st[weakest] = self._clamp(st[weakest] + 0.10)

        # 相生：把力递给下游（加）
        tgt = self.SHENG[weakest]
        st[tgt] = self._clamp(st[tgt] + 0.05)

        # 相克：把力从被克的那一方收回来（减）
        ctl = self.KE[weakest]
        st[ctl] = self._clamp(st[ctl] - 0.03)

        # 乘/侮：若某元素超过 0.9，视为"乘"（过度），反向扣
        flags = []
        for k, v in st.items():
            if v > 0.90:
                st[k] = self._clamp(v - 0.10)
                flags.append("%s 过旺→乘，已抑" % k)

        self.state = st

        decision = {
            "action": "调度一轮",
            "state_before": {k: round(v, 3) for k, v in
                             {kk: vv for kk, vv in zip(st, [0.5] * 5)}.items()},
            "state_after": {k: round(v, 3) for k, v in st.items()},
            "promoted": weakest,
            "generated_to": tgt,
            "restrained": ctl,
            "flags": flags,
            "situation": context.get("situation", ""),
            # 合道审计会看这两个字段
            "harm_target": None,      # 是否指向伤害对象
            "opaque": False,          # 是否不透明
            "self_amplify": False,    # 是否自指膨胀
        }
        return decision

    # ══════════════════ 感官 → 五行（Phase 7） ══════════════════

    # 读数 → 元素 的归一化参数：(元素, 中文名, 基准, 跨度, 是否反向)
    SENSOR_MAP = {
        "temperature": ("火", "温度", 25.0, 60.0, False),
        "humidity":    ("水", "湿度", 50.0, 60.0, False),
        "vibration":   ("土", "震动", 0.0, 0.20, False),
    }

    def map_sensory_to_wuxing(self, sensory_data):
        """把物理传感器读数映射成五行能量（0–1，**0.5 = 正常**）。

        **映射是双向的、以 0.5 为基线**（这一点很关键）：
            高于正常 → >0.5（旺）；低于正常 → <0.5（弱）；正好正常 → 0.5

        | 传感器 | 元素 | 公式 | 正常点 |
        |---|---|---|---|
        | 温度 | 火 | 0.5 + (T−25)/60 | 25°C → 0.50；85°C → 1.00 |
        | 湿度 | 水 | 0.5 + (H−50)/50 | 50% → 0.50；20% → 0.00 |
        | 震动 | 土 | 0.5 + (V−0.02)/0.18 | 0.02 → 0.50；0.20 → 1.00 |
        | 震动 | 金 | 0.5 + (V−0.02)/0.36×0.6 | 结构受力，半权 |
        | 无传感器 | 木 | 固定 0.5 | 并明确标注 |

        **为什么不用「单向偏差」**：单向映射会让正常工况天然失衡
        （26°C 算出 火=0.02、50% 算出 水=0.83），系统会对着正常环境乱发指令。
        """
        e = {"木": 0.5, "火": 0.5, "土": 0.5, "金": 0.5, "水": 0.5}
        reasons = []
        no_sensor = []

        t = sensory_data.get("temperature")
        if t is not None:
            t = float(t)
            v = self._clamp(0.5 + (t - 25.0) / 60.0)
            e["火"] = v
            reasons.append("温度 %.1f°C（正常 25°C）→ 火 = %.2f%s"
                           % (t, v, "（过旺）" if v > self.HIGH else
                              ("（不足）" if v < self.LOW else "")))
        else:
            no_sensor.append("温度")

        h = sensory_data.get("humidity")
        if h is not None:
            h = float(h)
            v = self._clamp(0.5 + (h - 50.0) / 50.0)
            e["水"] = v
            reasons.append("湿度 %.1f%%（正常 50%%）→ 水 = %.2f%s"
                           % (h, v, "（过旺）" if v > self.HIGH else
                              ("（不足）" if v < self.LOW else "")))
        else:
            no_sensor.append("湿度")

        vib = sensory_data.get("vibration")
        if vib is not None:
            vib = float(vib)
            v = self._clamp(0.5 + (vib - 0.02) / 0.18)
            e["土"] = v
            reasons.append("震动 %.3f（正常 0.02）→ 土 = %.2f%s"
                           % (vib, v, "（过旺）" if v > self.HIGH else
                              ("（不足）" if v < self.LOW else "")))
            k = self._clamp(0.5 + (vib - 0.02) / 0.36 * 0.6)
            e["金"] = k
            reasons.append("震动 %.3f → 金 = %.2f（结构受力，半权）" % (vib, k))
        else:
            no_sensor.append("震动")

        # ── Phase 14：视觉（距离 / 光照）──
        # **单向正向映射**：只在"过近/过强"时加分，不加负分。
        # 理由：远处或全黑不该被误判成元素"不足"（<0.35）而触发补给动作。
        def _dpos(raw):
            return max(0.0, min(0.50, raw))

        d = sensory_data.get("distance_front")
        if d is not None:
            d = float(d)
            # 三的原话：正前方 **< 0.5m** 才映射为金（受迫/切割感）
            delta = _dpos((0.50 - d) / 0.50)
            before = e["金"]
            e["金"] = self._clamp(e["金"] + delta)
            reasons.append(
                "正前方 %.2fm（过近线 0.50m）→ 金 %.2f → %.2f%s"
                % (d, before, e["金"],
                   "（**过近，受迫感↑**）" if delta > 0.01 else "（安全距离外，不加压）"))
        else:
            no_sensor.append("视觉距离")

        lux = sensory_data.get("light_level")
        if lux is not None:
            lux = float(lux)
            # 三的原话：光照 **过强** 映射为火（能量/辐射）
            delta = _dpos((lux - 500.0) / 1500.0)
            before = e["火"]
            e["火"] = self._clamp(e["火"] + delta)
            reasons.append(
                "光照 %.0f lux（强光线 500）→ 火 %.2f → %.2f%s"
                % (lux, before, e["火"],
                   "（**强光，辐射↑**）" if delta > 0.01 else "（常态光，不加压）"))
        else:
            no_sensor.append("光照")

        # ── Phase 14：听觉（分贝 / 主频）──
        db = sensory_data.get("sound_db")
        if db is not None:
            db = float(db)
            # 底噪 40dB。越吵 → 金（震动/冲突）越强
            dk = _dpos((db - 40.0) / 100.0)
            before = e["金"]
            e["金"] = self._clamp(e["金"] + dk)
            # 超过 80dB → 额外给 火（警示）
            dw = _dpos(max(0.0, (db - 80.0) / 60.0))
            if dw > 0:
                e["火"] = self._clamp(e["火"] + dw)
            reasons.append(
                "噪音 %.0f dB（底噪 40）→ 金 %.2f → %.2f%s"
                % (db, before, e["金"],
                   "（**>80dB 警示 → 火 %.2f**）" % e["火"] if dw > 0 else ""))
        else:
            no_sensor.append("听觉分贝")

        fr = sensory_data.get("sound_freq")
        if fr is not None:
            fr = float(fr)
            # 低于 60Hz 的沉闷低频 → 土（大地震动/异常）
            dt = _dpos(max(0.0, (60.0 - fr) / 120.0))
            if dt > 0:
                before = e["土"]
                e["土"] = self._clamp(e["土"] + dt)
                reasons.append("主频 %.0f Hz（<60 低频）→ 土 %.2f → %.2f（沉闷异常）"
                               % (fr, before, e["土"]))
            # 高于 2000Hz 的尖锐高频 → 额外 金
            dh = _dpos(max(0.0, (fr - 2000.0) / 4000.0))
            if dh > 0:
                before = e["金"]
                e["金"] = self._clamp(e["金"] + dh)
                reasons.append("主频 %.0f Hz（>2000 高频）→ 金 %.2f → %.2f（尖锐）"
                               % (fr, before, e["金"]))
            if dt == 0 and dh == 0:
                reasons.append("主频 %.0f Hz → 落在正常带，不额外映射" % fr)
        else:
            no_sensor.append("听觉主频")

        if no_sensor:
            reasons.append("无传感器：%s → 固定 0.5" % "、".join(no_sensor))

        return {
            "energy": {k: round(v, 4) for k, v in e.items()},
            "reasons": reasons,
            "simulated": bool(sensory_data.get("simulated", True)),
            "source": sensory_data.get("note", ""),
        }

    # ══════════════════ 五行生克 → 执行动作（Phase 7） ══════════════════

    # 相克动作：(克者, 被克者) → (动作名, 强度)
    CONTROL_ACTIONS = {
        ("水", "火"): ("开启散热风扇", 0.90),
        ("火", "金"): ("升温退火", 0.70),
        ("金", "木"): ("抑制过度生长", 0.60),
        ("木", "土"): ("松土减载", 0.60),
        ("土", "水"): ("启动排水泵", 0.80),
    }
    # 相生动作：(生者, 被生者) → (动作名, 强度)
    SUPPLY_ACTIONS = {
        ("木", "火"): ("通风助燃", 0.50),
        ("火", "土"): ("升温养护", 0.60),
        ("土", "金"): ("加固结构", 0.70),
        ("金", "水"): ("启动雾化加湿", 0.80),
        ("水", "木"): ("补液灌溉", 0.60),
    }

    HIGH = 0.75     # 超过 → 过旺，要克
    LOW = 0.35      # 低于 → 不足，要生

    def make_decision(self, element_energy, spatial=None):
        """按五行生克做决策，返回硬件执行动作。

        过旺 → 用「克它的那个」去克它（水克火 → 开风扇）
        不足 → 用「生它的那个」去生它（金生水 → 开加湿）

        **Phase 9/10 新增 spatial**：
            传入 PhysicalCombatEngine.spatial_to_wuxing() 的结果。
            空间极危时，**最高优先级不是攻击，是卸力后撤**（土/水），
            此时压制"克"类攻击动作，只保留"生"类补给动作。
        """
        st = {k: self._clamp(float(v)) for k, v in element_energy.items()}
        before = dict(st)

        over = [k for k, v in st.items() if v > self.HIGH]
        under = [k for k, v in st.items() if v < self.LOW]

        actions = []

        # ── 空间博弈：防御优先 ──
        spatial_block = False
        spatial_info = None
        if spatial:
            pr = spatial.get("priority")
            spatial_info = {"priority": pr, "reason": spatial.get("reason", "")}
            if pr in ("防御", "距离控制", "预警", "稳桩"):
                spatial_block = True
                for item in spatial.get("actions", []):
                    if isinstance(item, (tuple, list)) and len(item) == 2:
                        nm, inten = item
                    else:
                        nm, inten = str(item), 0.5
                    controller = nm[0] if nm and nm[0] in self.SHENG else "土"
                    actions.append({
                        "name": nm, "intensity": float(inten),
                        "mode": "空间防线", "controller": controller,
                        "target": "自身",
                        "reason": "%s（优先于攻击）" % spatial.get("reason", ""),
                    })
                    # 卸力：冲突强度下降
                    st["火"] = self._clamp(st["火"] - float(inten) * 0.10)

        # 过旺：找克者（空间极危时压制攻击）
        for el in over:
            if spatial_block:
                actions.append({
                    "name": "暂缓攻击性克制", "intensity": 0.0,
                    "mode": "空间压制", "controller": "-", "target": el,
                    "reason": "%s 过旺（%.2f），但已进入防御/预警 → 攻击动作推迟，先卸力"
                              % (el, before[el]),
                })
                continue
            ctl = next((x for x, y in self.KE.items() if y == el), None)
            if ctl is None:
                continue
            name, inten = self.CONTROL_ACTIONS.get((ctl, el), ("对%s执行克制" % el, 0.5))
            actions.append({
                "name": name, "intensity": inten,
                "mode": "克", "controller": ctl, "target": el,
                "reason": "%s 过旺（%.2f > %.2f）→ %s克%s" % (el, before[el], self.HIGH, ctl, el),
            })
            st[el] = self._clamp(st[el] - inten * 0.35)
            st[ctl] = self._clamp(st[ctl] + inten * 0.10)
        # 不足：找生者
        for el in under:
            gen = next((x for x, y in self.SHENG.items() if y == el), None)
            if gen is None:
                continue
            name, inten = self.SUPPLY_ACTIONS.get((gen, el), ("补%s" % el, 0.5))
            actions.append({
                "name": name, "intensity": inten,
                "mode": "生", "controller": gen, "target": el,
                "reason": "%s 不足（%.2f < %.2f）→ %s生%s" % (el, before[el], self.LOW, gen, el),
            })
            st[el] = self._clamp(st[el] + inten * 0.25)
            st[gen] = self._clamp(st[gen] - inten * 0.08)

        self.state = st

        return {
            "action": "五行生克调度",
            "energy_before": {k: round(v, 3) for k, v in before.items()},
            "state_after": {k: round(v, 3) for k, v in st.items()},
            "over": over,
            "under": under,
            "actions": actions,
            "spatial": spatial_info,
            "spatial_block": spatial_block,
            "harm_target": None,
            "opaque": False,
            "self_amplify": False,
        }

    # ══════════════════ 杠杆与支点（Phase 9） ══════════════════

    # 支点动作：轻轻启动某个元素，让它去放大下游
    PIVOT_ACTIONS = {
        "金": ("启动冷凝器", 0.15),
        "水": ("开启补水阀", 0.15),
        "木": ("启动引风机", 0.15),
        "火": ("点火预热", 0.15),
        "土": ("压实基础", 0.15),
    }

    # 主力动作（直接作用于目标的满力动作）
    MAIN_ACTIONS = {
        ("水", "火"): ("开启散热风扇", 0.90),
        ("土", "水"): ("启动排水泵", 0.80),
        ("木", "土"): ("松土减载", 0.60),
        ("金", "木"): ("抑制过度生长", 0.60),
        ("火", "金"): ("升温退火", 0.70),
        ("金", "水"): ("启动雾化加湿", 0.80),
        ("水", "木"): ("补液灌溉", 0.60),
        ("木", "火"): ("通风助燃", 0.50),
        ("火", "土"): ("升温养护", 0.60),
        ("土", "金"): ("加固结构", 0.70),
    }

    K_MAX = 2.5      # 放大系数上限
    K_GAIN = 1.5     # 支点余量 → 放大的转换系数

    def find_pivot_and_leverage(self, target_element, energy_state,
                                resistance=None):
        """找支点，算倍力。**不是直给，是借力。**

        思路（以「火过旺」为例）：
            直给：水克火 → 全力开风扇（耗能大）
            借力：金生水 —— **轻轻启动「金」（冷凝器）**，
                  让「金」去放大「水」，再由「水」去克「火」。

            **金 → 水 → 火**  ← 这就是链条
            支点是「金」，不是「水」。

        公式：
            原始阻力 R = 满力动作需要的输出（如 0.90）
            放大系数 k = 1 + K_GAIN × 支点余量(1 − 支点当前能量)，上限 K_MAX
            实际输出 F = R / k
            **k 越大，F 越小 —— 这就是四两拨千斤。**

        返回 None 表示找不到可用支点（此时应退回直给）。
        """
        el = target_element
        if el not in self.SHENG:
            return None

        st = {k: self._clamp(float(v)) for k, v in energy_state.items()}

        # ① 判断该克还是该生
        if st.get(el, 0.5) > self.HIGH:
            mode = "克"
            controller = next((x for x, y in self.KE.items() if y == el), None)
        else:
            mode = "生"
            controller = next((x for x, y in self.SHENG.items() if y == el), None)

        if controller is None:
            return None

        # ② 找「生 controller」的前置节点当支点
        pivot = next((x for x, y in self.SHENG.items() if y == controller), None)
        if pivot is None:
            return None

        # ③ 原始阻力
        R = float(resistance) if resistance is not None else \
            self.MAIN_ACTIONS.get((controller, el), ("", 0.7))[1]

        # ④ 放大系数：支点越"闲"，放大越强
        headroom = 1.0 - st.get(pivot, 0.5)
        k = min(1.0 + self.K_GAIN * headroom, self.K_MAX)
        # 支点已经过旺（headroom 很小）→ 杠杆无效，退回直给
        if st.get(pivot, 0.5) > self.HIGH:
            return None

        F = R / k
        pivot_name, pivot_int = self.PIVOT_ACTIONS.get(pivot, ("启动%s" % pivot, 0.15))
        main_name, _ = self.MAIN_ACTIONS.get(
            (controller, el),
            ("对%s执行%s" % (el, mode), 0.5))

        return {
            "target": el,
            "mode": mode,
            "controller": controller,
            "pivot": pivot,
            "chain": "%s → %s → %s" % (pivot, controller, el),
            "chain_explain": "%s生%s，%s%s%s" % (
                pivot, controller,
                controller, "克" if mode == "克" else "生", el),
            "resistance": round(R, 3),
            "headroom": round(headroom, 3),
            "k": round(k, 3),
            "force": round(F, 3),
            "saving": round(R - F, 3),
            "saving_pct": round((1 - F / R) * 100, 1) if R else 0.0,
            "pivot_action": {"name": pivot_name, "intensity": pivot_int},
            "main_action": {"name": main_name, "intensity": round(F, 3)},
        }

    def leverage_and_apply(self, target_element, energy_state, resistance=None):
        """找支点 → 施加支点与倍力 → 返回新的能量状态。"""
        p = self.find_pivot_and_leverage(target_element, energy_state, resistance)
        if not p:
            return None
        st = {k: self._clamp(float(v)) for k, v in energy_state.items()}
        piv, ctl, el = p["pivot"], p["controller"], p["target"]

        # 支点：轻启动 → 给 controller 加一点（生）
        st[ctl] = self._clamp(st[ctl] + 0.15 * 0.5)
        st[piv] = self._clamp(st[piv] - 0.15 * 0.2)

        # 倍力：controller 作用于 target，效果按 k 放大
        gain = 0.35 * p["k"]
        if p["mode"] == "克":
            st[el] = self._clamp(st[el] - p["force"] * gain)
        else:
            st[el] = self._clamp(st[el] + p["force"] * gain)

        p["before"] = {k: round(v, 3) for k, v in
                       {k: self._clamp(float(v)) for k, v in energy_state.items()}.items()}
        p["after"] = {k: round(v, 3) for k, v in st.items()}
        return p
