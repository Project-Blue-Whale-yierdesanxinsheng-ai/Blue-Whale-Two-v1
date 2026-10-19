# -*- coding: utf-8 -*-
"""07 · 多智能体蜂群阵法（三体协同）。

三的原话：三台节点，一个主攻（火），一个主防（土/水），一个辅助/截击（金/木）。

两条协同规则（都来自五行生克，不是编的）：
    1. **相生补给**：主攻的「火」不足时，辅助用「木」去生它（木生火）
    2. **引力掩护**：主防受威胁时，用引力场把辅助位「拉」过来挡（F = G·M·m/r²）

角色分配按节点的五行能量实况定，不是写死名字。
"""

import math


class SwarmTactics:
    """三体阵型：主攻 / 主防 / 辅助。"""

    # 角色 → 判定该角色的元素（谁在这些元素上能量最高，谁担任）
    ROLE_ELEMENTS = {
        "主攻": ["火"],
        "主防": ["土", "水"],
        "辅助": ["金", "木"],
    }

    # 相生补给：主攻缺什么，辅助用什么生
    SUPPLY = {
        "火": ("木", "木生火"),
        "土": ("火", "火生土"),
        "金": ("土", "土生金"),
        "水": ("金", "金生水"),
        "木": ("水", "水生木"),
    }

    G = 1.0

    def __init__(self, nodes=None):
        # nodes: {"A": {"energy": {五行: 值}, ...}, ...}
        self.nodes = nodes or {}
        self.roles = {}
        self.log = []

    # ══════════ ① 角色分配 ══════════
    def assign_roles(self, nodes=None):
        """按五行能量实况分配三个角色。"""
        ns = nodes if nodes is not None else self.nodes
        self.nodes = ns
        ids = sorted(ns.keys())
        if len(ids) < 3:
            raise ValueError("三体阵型至少需要 3 个节点，现在只有 %d 个" % len(ids))

        # 每个角色找"在该角色元素上能量最高"的节点（不重复占位）
        used = set()
        roles = {}
        for role in ("主攻", "主防", "辅助"):
            els = self.ROLE_ELEMENTS[role]
            best, best_v = None, -1.0
            for nid in ids:
                if nid in used:
                    continue
                e = ns[nid].get("energy", {})
                v = sum(float(e.get(x, 0.0)) for x in els)
                if v > best_v:
                    best, best_v = nid, v
            roles[role] = best
            used.add(best)

        self.roles = roles
        out = {"roles": roles,
               "detail": {r: {"node": n,
                              "energy": {k: round(float(v), 2)
                                         for k, v in ns[n].get("energy", {}).items()},
                              "score": round(sum(float(ns[n].get("energy", {}).get(x, 0))
                                                 for x in self.ROLE_ELEMENTS[r]), 3)}
                          for r, n in roles.items()}}
        self.log.append(("assign", out))
        return out

    # ══════════ ② 协同 ══════════
    def coordinate(self, threat=None):
        """跑一轮协同：相生补给 ＋ 引力掩护。

        threat: {"target": "主防", "level": "极高"} 或 None
        """
        if not self.roles:
            self.assign_roles()

        atk = self.roles["主攻"]
        dfn = self.roles["主防"]
        sup = self.roles["辅助"]
        E = {n: dict(self.nodes[n].get("energy", {})) for n in (atk, dfn, sup)}

        out = {"roles": dict(self.roles), "directives": [], "transfers": []}

        # ── 规则 1：主攻的「火」不足 → 辅助用相生补 ──
        fire = float(E[atk].get("火", 0.0))
        if fire < 0.60:
            gen_el, why = self.SUPPLY["火"]           # 木生火
            have = float(E[sup].get(gen_el, 0.0))
            give = round(min(0.25, have * 0.5), 3)     # 辅助最多让出一半
            if give > 0:
                out["transfers"].append({
                    "from": sup, "to": atk,
                    "element": gen_el, "amount": give,
                    "why": "主攻火=%.2f 不足 → %s（%s %.2f）"
                           % (fire, why, gen_el, have),
                })
                out["directives"].append(
                    "%s 把 %s（%.2f）相生给 %s —— 木生火，火起" % (sup, gen_el, give, atk))
            else:
                out["directives"].append(
                    "主攻火=%.2f 不足，但辅助的%s也只有 %.2f → 补不动，需要外部补木"
                    % (fire, gen_el, have))
        else:
            out["directives"].append("主攻火=%.2f 充足，无需补给" % fire)

        # ── 规则 2：主防受威胁 → 引力拉扯辅助过来挡 ──
        if threat and threat.get("target") == "主防":
            lvl = threat.get("level", "高")
            # 引力：主防 - 辅助
            m_d = 1.0 + sum(float(v) for v in E[dfn].values())
            m_s = 1.0 + sum(float(v) for v in E[sup].values())
            r = 1.0 if lvl in ("高", "极高") else 2.0
            F = self.G * m_d * m_s / (r * r)
            pull = round(min(0.8, F / (m_d + m_s)), 3)
            out["gravity"] = {
                "from": sup, "to": dfn,
                "m_defender": round(m_d, 3), "m_support": round(m_s, 3),
                "r": r, "F": round(F, 3), "pull": pull,
                "why": "三体引力 F = G·M·m/r² = %.2f/%.2f = %.2f" % (m_d * m_s, r * r, F),
            }
            out["directives"].append(
                "威胁=%s → 引力拉扯：%s 向 %s 靠拢（F=%.2f，拉近 %.2f）"
                % (lvl, sup, dfn, F, pull))
            # 掩护时辅助的「土/水」提权
            E[sup]["土"] = min(1.0, float(E[sup].get("土", 0)) + pull * 0.4)
            E[sup]["水"] = min(1.0, float(E[sup].get("水", 0)) + pull * 0.3)
            out["directives"].append(
                "  %s 掩护姿态：土 +%.2f ／ 水 +%.2f（挡在前面）"
                % (sup, pull * 0.4, pull * 0.3))
        elif threat:
            out["directives"].append(
                "威胁目标=%s，不在主防身上 → 不触发引力掩护" % threat.get("target"))

        out["energy_after"] = {n: {k: round(float(v), 3) for k, v in e.items()}
                               for n, e in E.items()}
        out["harm_target"] = None
        out["opaque"] = False
        out["self_amplify"] = False
        self.log.append(("coordinate", out))
        return out

    # ══════════ ③ 汇总 ══════════
    def summary(self):
        return {
            "nodes": len(self.nodes),
            "roles": dict(self.roles),
            "rounds": len([x for x in self.log if x[0] == "coordinate"]),
        }
