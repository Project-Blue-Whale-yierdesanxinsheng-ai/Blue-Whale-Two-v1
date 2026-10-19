# -*- coding: utf-8 -*-
"""06 · 物理博弈与力学（PhysicalCombatEngine）。

三的原话（两层）：
    第一层：手脚长度决定的相对安全空间 —— **打得到 vs 够不着**
    第二层：同臂展下，计算对方力传导的轨迹与支点，**半路截击**（截拳道）

核心概念：
    安全区 = (对方臂展, 我方臂展)   ← 只有在这个区间里，我能打到他、他够不到我
    相手形成支点的时刻 = 动能峰值 = 他全身重量都压进去的那一下
    **所以必须在峰值之前动手 —— 那就是截击。**

不接真硬件，纯计算。所有数字都是模型推演，不是实测。
"""

import math


class PhysicalCombatEngine:
    """物理空间博弈引擎：安全距离 + 轨迹截击。"""

    # 判定阈值（米）
    NEAR_STEP = 0.60      # 距对方臂展不足这个数 → 一步之内，判危险
    CONTACT_EPS = 0.05    # 距离差小于这个 → 认为贴身

    def __init__(self):
        self.last = {}

    # ══════════════ ① 安全距离 ══════════════
    def calculate_safe_distance(self, my_reach, enemy_reach, distance=None):
        """算安全区。

        my_reach / enemy_reach: 臂展（米）
        distance: 当前双方间距（米，可选）

        返回：
            advantage  我 − 对方（正=优势，负=劣势）
            safe_zone  (lo, hi) 或 None（无安全区）
            level      优势 / 均势 / 劣势
            verdict / recommendation
        """
        r_me, r_en = float(my_reach), float(enemy_reach)
        adv = r_me - r_en
        out = {"my_reach": r_me, "enemy_reach": r_en,
               "advantage": round(adv, 3)}

        if adv > 0:
            lo, hi = r_en, r_me
            out["safe_zone"] = (round(lo, 3), round(hi, 3))
            out["level"] = "优势"
            out["verdict"] = "对方够不到我，我打得到他"
            out["recommendation"] = (
                "保持距离在 %.2f–%.2f m 之间；出这个区间就失去优势" % (lo, hi))
        elif adv < 0:
            out["safe_zone"] = None
            out["level"] = "劣势"
            out["verdict"] = "对方臂展多 %.2f m，**没有安全区**" % (-adv)
            out["recommendation"] = (
                "后撤到 %.2f m 以外，或贴身（< %.2f m）破掉他的长臂优势"
                % (r_en, r_en - r_me if r_en > r_me else 0.0))
        else:
            out["safe_zone"] = None
            out["level"] = "均势"
            out["verdict"] = "臂展相当，没有绝对安全区"
            out["recommendation"] = "只能靠时机与截击取胜（见 intercept_strike）"

        if distance is not None:
            d = float(distance)
            out["distance"] = d
            out["gap_to_enemy_reach"] = round(d - r_en, 3)
            out["gap_to_my_reach"] = round(d - r_me, 3)
            out["enemy_can_hit"] = d <= r_en
            out["i_can_hit"] = d <= r_me

            if d <= r_en and d <= r_me:
                out["zone"] = "交换区"          # 双方都够得到
                out["danger"] = "高"
            elif d <= r_en:
                out["zone"] = "挨打区"          # 只有对方够得到
                out["danger"] = "极高"
            elif (r_en < d <= r_me) if adv > 0 else False:
                out["zone"] = "安全区"
                out["danger"] = "低"
            elif d - r_en <= self.NEAR_STEP:
                out["zone"] = "临界区"
                out["danger"] = "中"
                out["verdict_dynamic"] = (
                    "对方还差 %.2f m 就进入攻击范围 —— **一步之内**" % (d - r_en))
            else:
                out["zone"] = "距离外"
                out["danger"] = "低"

            # 极危：对方已能打到我，且他臂展更长
            out["critical"] = bool(out["enemy_can_hit"] and adv < 0)

        self.last["safe_distance"] = out
        return out

    # ══════════════ ② 力的传导轨迹 ══════════════
    def calculate_intercept_point(self, enemy_trajectory, time_step=0.02):
        """采样对方出拳的力传导轨迹。

        enemy_trajectory 需要：
            distance  当前间距（米）
            speed     拳速（米/秒）
            mass      有效质量（kg，可选，默认 6）
            t_peak    动能峰值时刻（可选，默认=到达时刻）

        模型：
            拳头从 distance 打到 0，用时 t_hit = distance / speed
            **动能峰值就在 t_hit**（全身重量压进去，支点形成）
            力随位移增长：F(t) ∝ (v·t / distance)² × 0.5 + 0.5·(t/t_hit)
        """
        tr = dict(enemy_trajectory)
        d = float(tr.get("distance", 1.8))
        v = float(tr.get("speed", 4.5))
        m = float(tr.get("mass", 6.0))
        if v <= 0:
            raise ValueError("speed 必须大于 0")

        t_hit = d / v                       # 打到身上的时刻
        t_peak = float(tr.get("t_peak", t_hit))   # 动能峰值 = 支点形成

        samples = []
        t = 0.0
        while t <= t_peak + 1e-9:
            prog = min(t / t_peak, 1.0) if t_peak else 1.0
            pos = d * (1.0 - prog)                      # 拳头位置
            # 力：前段加速度上升，后段靠体重压进去
            f = 0.5 * (prog ** 2) + 0.5 * prog
            ke = 0.5 * m * (v * prog) ** 2              # 动能
            samples.append({
                "t": round(t, 4),
                "pos": round(pos, 4),
                "force_ratio": round(f, 4),
                "kinetic": round(ke, 3),
            })
            t += float(time_step)

        out = {
            "t_hit": round(t_hit, 4),
            "t_peak": round(t_peak, 4),
            "samples": samples,
            "n": len(samples),
            "peak_kinetic": round(0.5 * m * v * v, 3),
        }
        self.last["trajectory"] = out
        return out

    # ══════════════ ③ 截击（截拳道） ══════════════
    def intercept_strike(self, enemy_trajectory, lead_time=0.20, time_step=0.01):
        """在对方动能峰值之前动手 —— 半路截断。

        逻辑：
            他的力在 t_peak 达到最大（支点形成，全身重心压进去）
            **在他还没形成支点前打掉发力链，他自己就倒了**
            截击点取 t_peak − lead_time

        返回：时机、距离、当时的力占比、调用哪个五行、动作与强度
        """
        traj = self.calculate_intercept_point(enemy_trajectory, time_step)
        t_peak = traj["t_peak"]
        t_int = max(0.0, t_peak - float(lead_time))

        # 取最接近 t_int 的样本
        best = min(traj["samples"], key=lambda s: abs(s["t"] - t_int))
        ratio = best["force_ratio"]

        # 拦截越早，对方力越小，我方越省力（这也是杠杆逻辑）
        # 五行选择：早 → 金（切割，断其形）；晚 → 火（爆发，抢时间）
        if ratio < 0.55:
            element, action, why = "金", ("截击·切其发力链", 0.55), "力未成形 → 以金断之"
        else:
            element, action, why = "火", ("截击·抢爆发先手", 0.75), "力将成形 → 以火抢之"

        out = {
            "t_peak": t_peak,
            "t_intercept": round(best["t"], 4),
            "lead_time": round(t_peak - best["t"], 4),
            "intercept_pos": best["pos"],
            "intercept_distance_to_me": best["pos"],
            "force_ratio_at_intercept": ratio,
            "force_saving_pct": round((1.0 - ratio) * 100, 1),
            "peak_kinetic": traj["peak_kinetic"],
            "kinetic_at_intercept": best["kinetic"],
            "element": element,
            "action": action[0],
            "intensity": action[1],
            "why": why,
            "verdict": "在峰值前 %.2f 秒截断（此时他的力只有峰值的 %.0f%%）"
                       % (t_peak - best["t"], ratio * 100),
        }
        self.last["intercept"] = out
        return out

    # ══════════════ ④ 桥接五行：空间状态 → 变招 ══════════════
    def spatial_to_wuxing(self, safe):
        """把空间态势翻译成五行变招。

        极危（对方长臂展近身）→ **土/水优先**（卸力、后撤），不是硬攻。
        """
        if not safe:
            return {"priority": "none", "elements": [], "reason": ""}

        if safe.get("critical"):
            return {
                "priority": "防御",
                "elements": ["土", "水"],
                "reason": "对方臂展更长且已能击中我 → 不硬拼，先卸力后撤",
                "actions": [("土·卸力卸根", 0.60), ("水·化劲后撤", 0.70)],
            }
        lvl = safe.get("level")
        if lvl == "劣势":
            return {
                "priority": "距离控制",
                "elements": ["水", "土"],
                "reason": "处于劣势但对方还够不到 → 用水控距、土稳桩",
                "actions": [("水·控距", 0.45), ("土·稳桩", 0.40)],
            }
        if lvl == "均势":
            return {
                "priority": "时机",
                "elements": ["金", "火"],
                "reason": "臂展相当 → 靠截击，不靠硬拼",
                "actions": [("金·截击", 0.55)],
            }
        return {
            "priority": "控场",
            "elements": ["木", "火"],
            "reason": "我方臂展更长 → 用距离逼他，不必冒险",
            "actions": [("木·控距压迫", 0.40)],
        }


class BruceLeeFootwork:
    """李小龙步法：动态蓄能。

    三的原话要的两件事：
        1. **抖动**：双脚交互跳动，输出迷惑性的微小位移（增加对手预测难度）
        2. **蓄能**：脚跟微离地的「静→动」转换，在跳动中积累弹性势能

    联动：先蓄能 → 截击的 `lead_time` 可以缩短（敢等），或威力提升。
    """

    SPRING_K = 0.8        # 蓄能速率（每秒）
    MAX_ENERGY = 1.0      # 弹性势能上限
    JITTER_MAX = 0.12     # 单次最大抖动位移（米）
    PRED_DECAY = 0.18     # 每次抖动降低的可预测性

    def __init__(self):
        self.energy = 0.0          # 弹性势能 0–1
        self.jitter_count = 0
        self.predictability = 1.0  # 1=完全可预测，越跳越小
        self.log = []

    @staticmethod
    def _clamp(v):
        return max(0.0, min(1.0, float(v)))

    # ────────── ① 抖动 ──────────
    def jitter_movement(self, intensity=0.6):
        """一次交互跳动的微小位移。

        用确定性的伪随机（正弦叠加），保证可复现 —— 不用 random。
        """
        i = self._clamp(intensity)
        n = self.jitter_count
        # 两个不整除的频率，形成非周期轨迹
        dx = self.JITTER_MAX * i * math.sin(n * 1.7)
        dy = self.JITTER_MAX * i * math.cos(n * 2.3)
        self.jitter_count += 1
        self.predictability = max(0.15, self.predictability - self.PRED_DECAY * i)

        out = {
            "n": n,
            "dx": round(dx, 4),
            "dy": round(dy, 4),
            "displacement": round(math.hypot(dx, dy), 4),
            "predictability": round(self.predictability, 3),
            "note": "位移微小但非周期 → 对手难预判落脚点",
        }
        self.log.append(("jitter", out))
        return out

    # ────────── ② 蓄能 ──────────
    def spring_energy_charge(self, time_step=0.05, steps=1):
        """脚跟微离地蓄能。**静 → 动 的那一下，力量从这里来。**"""
        dt = max(0.0, float(time_step))
        for _ in range(int(steps)):
            self.energy = self._clamp(self.energy + self.SPRING_K * dt)
        out = {
            "energy": round(self.energy, 3),
            "charge_pct": round(self.energy * 100, 1),
            "steps": int(steps),
            "note": "弹性势能 = %.2f（上限 1.0）" % self.energy,
        }
        self.log.append(("charge", out))
        return out

    # ────────── ③ 联动截击 ──────────
    def apply_charge(self, intercept, engine=None):
        """把蓄能接到截击上：敢等（缩短 lead_time）＋ 力量增强。

        intercept: PhysicalCombatEngine.intercept_strike() 的结果
        返回新的 intercept（不改原对象）
        """
        e = self.energy
        out = dict(intercept)

        # 蓄能越多，越敢等（lead_time 缩短），但有下限 0.03s
        base_lead = float(intercept["lead_time"])
        new_lead = max(0.03, base_lead - e * 0.10)
        out["lead_time_base"] = round(base_lead, 4)
        out["lead_time"] = round(new_lead, 4)
        out["lead_shortened"] = round(base_lead - new_lead, 4)

        # 越晚动手，对方力越大；但蓄能补上了这部分
        ratio = min(1.0, float(intercept["force_ratio_at_intercept"]) + e * 0.35)
        out["force_ratio_at_intercept"] = round(ratio, 4)
        out["kinetic_at_intercept"] = round(
            float(intercept.get("kinetic_at_intercept", 0.0)) * (1 + e * 0.5), 3)

        # 威力提升
        power_mult = 1.0 + e * 0.6
        out["power_mult"] = round(power_mult, 3)
        out["intensity_base"] = float(intercept["intensity"])
        out["intensity"] = round(min(1.0, float(intercept["intensity"]) * power_mult), 4)
        out["charged"] = e > 0
        out["energy"] = round(e, 3)
        out["why"] = ("蓄能 %.0f%% → 敢多等 %.2f s，威力 ×%.2f"
                      % (e * 100, base_lead - new_lead, power_mult)) if e > 0 else "未蓄能"
        self.log.append(("apply_charge", out))
        return out

    # ────────── ④ 状态 ──────────
    def status(self):
        return {
            "energy": round(self.energy, 3),
            "jitter_count": self.jitter_count,
            "predictability": round(self.predictability, 3),
        }
