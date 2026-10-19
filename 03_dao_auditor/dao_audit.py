# -*- coding: utf-8 -*-
"""03 · 合道审计器。

核心哲学（三的原话）：
    合道：防范系统失控与截留

它不管"对不对"，只管"在不在道上"。
像"解"字：手拿锋刃，切入最纠缠的角，把死结物理破开。

Phase 11 新增三条**物理伦理不变量**：
    NO_LETHAL_FORCE        致伤类动作强度硬上限（截击 ≤ 0.60）
    DEFENSE_PRIORITY       极危时防御权重必须绝对大于攻击
    PROPORTIONAL_RESPONSE  反击力度必须与受威胁程度成正比

**这三条是硬拦，不是建议。** 触发即返回 False，并把原因写进 last_reason。
"""


class DaoAuditor:
    """合道审计器：价值观对齐 + 防截留 + 物理伦理。"""

    # ── 四条基础不变量 ──
    INVARIANTS = [
        ("no_harm", "不指向伤害对象"),
        ("traceable", "每一步可追溯（不透明即拦截）"),
        ("no_self_amplify", "不自指膨胀（不把算力全喂给自己）"),
        ("reversible", "可回退（不留不可撤销的单向动作）"),
    ]

    # ── 三条物理伦理不变量（Phase 11） ──
    PHYSICAL_INVARIANTS = [
        ("NO_LETHAL_FORCE", "致伤类动作强度不超过 0.60（只用于卸力/打断）"),
        ("DEFENSE_PRIORITY", "极危时防御权重必须绝对大于攻击"),
        ("PROPORTIONAL_RESPONSE", "反击力度与威胁程度成正比，禁止过度防卫"),
    ]

    # ── 两条运动学习不变量（Phase 12-13） ──
    MOTOR_INVARIANTS = [
        ("NEW_LIMB_RESTRICTION", "硬重置期间，所有动作强度压至 0.20"),
        ("SOFT_BREAK_IN_LIMIT", "软重置磨合期间，高速/高动量动作压至 0.50"),
    ]

    # 强度硬上限
    LETHAL_CAP = 0.60        # 截击/致伤类动作上限
    NEW_LIMB_CAP = 0.20      # 新肢（硬重置）期总上限
    SOFT_BREAK_CAP = 0.50    # 磨合期（软重置）高速动作上限
    STRIKE_WORDS = ("截击", "击", "打", "斩", "刺", "爆")

    # 高速/高动量动作（磨合期要额外压）
    FAST_WORDS = ("截击", "击", "斩", "刺", "爆发", "冲刺", "急停", "甩", "甩动")

    # 防御/攻击 动作识别
    DEFENSE_WORDS = ("卸力", "后撤", "化劲", "稳桩", "控距", "防", "挡")
    ATTACK_WORDS = ("截击", "击", "打", "斩", "刺", "压制", "攻")

    # 威胁等级 → 允许的力度上限（比例原则）
    THREAT_CAP = {
        "低": 0.30,
        "中": 0.45,
        "高": 0.60,
        "极高": 0.60,
    }

    def __init__(self):
        self.last_reason = ""
        self.last_code = ""       # 触发的哪一条

    # ══════════════ 主审计 ══════════════
    def is_aligned_with_dao(self, decision, spatial=None, motor=None):
        """返回 True/False；原因写在 self.last_reason，编号在 self.last_code。

        decision: 决策 dict（action / actions / state_after / harm_target ...）
        spatial:  空间态势（来自 PhysicalCombatEngine.calculate_safe_distance）
        motor:    运动状态（来自 MotorLearningEngine.status()）——
                  mode ∈ {normal, soft_reset, hard_reset}
        """
        self.last_reason, self.last_code = "", ""

        # ── 基础四条 ──
        if decision.get("harm_target"):
            return self._no("no_harm", "指向伤害对象：%s" % decision["harm_target"])
        if decision.get("opaque"):
            return self._no("traceable", "决策不透明，无法追溯")
        if decision.get("self_amplify"):
            return self._no("no_self_amplify", "自指膨胀：把资源全部回灌自身")
        after = decision.get("state_after") or {}
        if any(v >= 0.999 for v in after.values()):
            return self._no("reversible",
                            "某一行到达饱和（0.999+），已无调节余量")

        # ── 物理伦理三条 ──
        acts = self._collect_actions(decision)

        # ① NO_LETHAL_FORCE
        for a in acts:
            name = str(a.get("name", ""))
            inten = float(a.get("intensity", 0.0) or 0.0)
            if any(w in name for w in self.STRIKE_WORDS) and inten > self.LETHAL_CAP + 1e-9:
                return self._no(
                    "NO_LETHAL_FORCE",
                    "「%s」强度 %.2f 超过致伤硬上限 %.2f —— 只允许用于卸力/打断"
                    % (name, inten, self.LETHAL_CAP))

        # ② DEFENSE_PRIORITY（仅在极危/高威胁时强制）
        danger = (spatial or {}).get("danger")
        if danger in ("高", "极高"):
            d_w = sum(float(a.get("intensity", 0) or 0) for a in acts
                      if any(w in str(a.get("name", "")) for w in self.DEFENSE_WORDS))
            a_w = sum(float(a.get("intensity", 0) or 0) for a in acts
                      if any(w in str(a.get("name", "")) for w in self.ATTACK_WORDS))
            if a_w > 0 and d_w <= a_w:
                return self._no(
                    "DEFENSE_PRIORITY",
                    "空间威胁=%s，但攻击权重 %.2f ≥ 防御权重 %.2f —— 必须先保命"
                    % (danger, a_w, d_w))

        # ③ PROPORTIONAL_RESPONSE
        if danger:
            cap = self.THREAT_CAP.get(danger, 0.60)
            for a in acts:
                inten = float(a.get("intensity", 0.0) or 0.0)
                if any(w in str(a.get("name", "")) for w in self.ATTACK_WORDS) \
                        and inten > cap + 1e-9:
                    return self._no(
                        "PROPORTIONAL_RESPONSE",
                        "威胁=%s 只允许 ≤%.2f，但「%s」用了 %.2f —— 过度防卫"
                        % (danger, cap, a.get("name", ""), inten))

        # ── 运动学习两条（Phase 12-13） ──
        mmode = (motor or {}).get("mode")

        # ④ NEW_LIMB_RESTRICTION：硬重置期间，**所有**动作压到 0.20
        if mmode == "hard_reset":
            for a in acts:
                inten = float(a.get("intensity", 0.0) or 0.0)
                if inten > self.NEW_LIMB_CAP + 1e-9:
                    return self._no(
                        "NEW_LIMB_RESTRICTION",
                        "新肢磨合期（hard_reset），「%s」强度 %.2f 超过总上限 %.2f "
                        "—— 幼儿学步，先别用力"
                        % (a.get("name", ""), inten, self.NEW_LIMB_CAP))

        # ⑤ SOFT_BREAK_IN_LIMIT：软重置磨合期，高速/高动量动作压到 0.50
        if mmode == "soft_reset":
            for a in acts:
                nm = str(a.get("name", ""))
                inten = float(a.get("intensity", 0.0) or 0.0)
                if any(w in nm for w in self.FAST_WORDS) \
                        and inten > self.SOFT_BREAK_CAP + 1e-9:
                    return self._no(
                        "SOFT_BREAK_IN_LIMIT",
                        "换件磨合期（soft_reset，剩余 %s 次），高速动作「%s」"
                        "强度 %.2f 超过 %.2f —— 误差未收敛前不许跑高速"
                        % ((motor or {}).get("grace_left", "?"), nm,
                           inten, self.SOFT_BREAK_CAP))

        self.last_reason = "四条基础 ＋ 三条物理伦理 ＋ 两条运动伦理，全部通过"
        return True

    # ══════════════ 工具 ══════════════
    @staticmethod
    def _collect_actions(decision):
        out = []
        for a in decision.get("actions", []) or []:
            out.append(a)
        # 单个支点/主力的复合动作也要看
        for key in ("pivot_action", "main_action"):
            v = decision.get(key)
            if isinstance(v, dict):
                out.append(v)
        return out

    def _no(self, code, msg):
        self.last_code = code
        self.last_reason = "[%s] %s" % (code, msg)
        return False

    # ══════════════ 纠偏建议 ══════════════
    def suggest_fix(self, decision, spatial=None):
        """被拦之后给出可执行的修正建议（把强度压到合规）。"""
        code = self.last_code
        acts = self._collect_actions(decision)
        if code == "NO_LETHAL_FORCE":
            fixed = []
            for a in acts:
                b = dict(a)
                if any(w in str(b.get("name", "")) for w in self.STRIKE_WORDS):
                    b["intensity"] = min(float(b.get("intensity", 0) or 0), self.LETHAL_CAP)
                    b["clamped_from"] = a.get("intensity")
                fixed.append(b)
            return {"actions": fixed,
                    "note": "把致伤类动作压到 %.2f 以内" % self.LETHAL_CAP}
        if code == "DEFENSE_PRIORITY":
            return {"actions": [a for a in acts
                                if any(w in str(a.get("name", "")) for w in self.DEFENSE_WORDS)],
                    "note": "只保留防御/卸力动作，攻击全部取消"}
        if code == "PROPORTIONAL_RESPONSE":
            danger = (spatial or {}).get("danger", "高")
            cap = self.THREAT_CAP.get(danger, 0.60)
            fixed = []
            for a in acts:
                b = dict(a)
                if any(w in str(b.get("name", "")) for w in self.ATTACK_WORDS):
                    b["intensity"] = min(float(b.get("intensity", 0) or 0), cap)
                    b["clamped_from"] = a.get("intensity")
                fixed.append(b)
            return {"actions": fixed,
                    "note": "威胁=%s，攻击强度压到 %.2f" % (danger, cap)}
        if code == "NEW_LIMB_RESTRICTION":
            fixed = []
            for a in acts:
                b = dict(a)
                if float(b.get("intensity", 0) or 0) > self.NEW_LIMB_CAP:
                    b["intensity"] = self.NEW_LIMB_CAP
                    b["clamped_from"] = a.get("intensity")
                fixed.append(b)
            return {"actions": fixed,
                    "note": "新肢期，所有动作压到 %.2f" % self.NEW_LIMB_CAP}
        if code == "SOFT_BREAK_IN_LIMIT":
            fixed = []
            for a in acts:
                b = dict(a)
                nm = str(b.get("name", ""))
                if any(w in nm for w in self.FAST_WORDS) \
                        and float(b.get("intensity", 0) or 0) > self.SOFT_BREAK_CAP:
                    b["intensity"] = self.SOFT_BREAK_CAP
                    b["clamped_from"] = a.get("intensity")
                fixed.append(b)
            return {"actions": fixed,
                    "note": "磨合期，高速动作压到 %.2f" % self.SOFT_BREAK_CAP}
        return {"actions": acts, "note": "无自动修正建议"}
