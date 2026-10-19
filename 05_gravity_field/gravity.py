# -*- coding: utf-8 -*-
"""05 · 开源引力场 / 概念引力场（GravityField）。

核心哲学（三的原话）：
    开源 = 旋转的中心引力场

两种节点：
    1. **开发者节点** —— 质量 = 贡献度（commit / bugfix / doc）
    2. **概念节点**   —— 质量 = 字条内容量（字数）；距离 = 共现强度倒数

物理公式（两个场景共用）：
    F = G·M·m / r²
    v_esc = sqrt(2GM/r)

**共现越频繁 → r 越小 → F 越大 → 概念自动聚类。**
"""

import math


class GravityField:
    """向心力模型：开发者与概念，同一套引力。"""

    def __init__(self, core_mass=1.0, G=1.0,
                 w_commit=1.0, w_bugfix=1.5, w_doc=0.5):
        self.core_mass = float(core_mass)
        self.G = float(G)
        # 贡献权重：修 bug 比提 commit 更值钱（救的是别人的时间）
        self.w_commit = w_commit
        self.w_bugfix = w_bugfix
        self.w_doc = w_doc
        self.nodes = {}

    # ── 节点质量 ──
    def node_mass(self, node):
        # 概念节点自带 mass，直接用
        if "mass" in node:
            return float(node["mass"])
        return (self.w_commit * float(node.get("commits", 0))
                + self.w_bugfix * float(node.get("bugfixes", 0))
                + self.w_doc * float(node.get("docs", 0)))

    # ══════════ ① 开发者节点 ══════════
    def attract(self, node):
        """接入新开发者节点，返回向心力与收敛预测。

        node: name, commits, bugfixes, docs, distance, velocity(可选)
        """
        name = node.get("name", "匿名节点")
        r = max(float(node.get("distance", 1.0)), 1e-6)
        m = self.node_mass(node)
        v = float(node.get("velocity", 0.0))

        force = self.G * self.core_mass * m / (r * r)
        accel = self.G * self.core_mass / (r * r)
        v_esc = math.sqrt(2.0 * self.G * self.core_mass / r)
        captured = v < v_esc
        new_r = max(r - accel, 1e-6) if captured else r + v

        rec = {
            "name": name, "kind": node.get("kind", "开发者"),
            "mass": round(m, 4), "distance": round(r, 4),
            "force": round(force, 4), "accel": round(accel, 4),
            "escape_velocity": round(v_esc, 4), "velocity": round(v, 4),
            "captured": captured, "next_distance": round(new_r, 4),
        }
        if m <= 0:
            rec["verdict"] = "零贡献 → 零引力，不会被捕获"
        elif not captured:
            rec["verdict"] = "速度 %.2f > 逃逸速度 %.2f → 飞离" % (v, v_esc)
        elif r <= 0.5:
            rec["verdict"] = "已在核心区（r≤0.5）"
        elif new_r <= 0.5:
            rec["verdict"] = "本轮将进入核心区"
        else:
            rec["verdict"] = "留在轨道，持续靠拢"

        self.nodes[name] = rec
        return rec

    def attract_many(self, nodes):
        return [self.attract(n) for n in nodes]

    # ══════════ ② 概念节点 ══════════
    @staticmethod
    def cooccur_distance(strength, floor=0.35, scale=2.0):
        """共现强度 → 距离。

        公式：r = floor + scale / (1 + strength)
        共现 0 次 → r = floor + scale = 2.35（远）
        共现 10 次 → r = floor + 2/11 ≈ 0.53（很近）
        **永不趋近 0** —— 概念之间总有最小距离，不会塌成一个点。
        """
        return floor + scale / (1.0 + max(float(strength), 0.0))

    def attract_concept(self, query, candidates, core_mass=None):
        """概念引力：以 query 为核心，算每个候选概念被吸多紧。

        candidates: [{name, mass, strength}]   strength = 与 query 的共现强度
        返回按 F 降序的列表。
        """
        M = float(core_mass if core_mass is not None else self.core_mass)
        out = []
        for c in candidates:
            m = self.node_mass(c)
            st = float(c.get("strength", 0.0))
            r = self.cooccur_distance(st)
            F = self.G * M * m / (r * r)
            out.append({
                "name": c.get("name", "?"),
                "kind": c.get("kind", "概念"),
                "mass": round(m, 4),
                "strength": st,
                "distance": round(r, 4),
                "force": round(F, 4),
                "source": c.get("source", ""),
            })
        out.sort(key=lambda x: -x["force"])
        for i, d in enumerate(out, 1):
            d["rank"] = i
        return out

    # ══════════ ③ 汇总 ══════════
    def core_report(self):
        if not self.nodes:
            return {"count": 0}
        ms = [n["mass"] for n in self.nodes.values()]
        rs = [n["distance"] for n in self.nodes.values()]
        return {
            "count": len(self.nodes),
            "total_mass": round(sum(ms), 4),
            "avg_distance": round(sum(rs) / len(rs), 4),
            "captured": sum(1 for n in self.nodes.values() if n["captured"]),
            "core_members": sum(1 for n in self.nodes.values() if n["distance"] <= 0.5),
        }


# ══════════════════════ 社区发现（标签传播） ══════════════════════

def label_propagation(node_names, edges, iters=40):
    """标签传播社区发现（异步更新 ＋ 确定性 tie-break）。

    node_names: 节点名列表
    edges:      [{"a":..,"b":..,"w":..}, ...]
    返回:       {标签: [节点名, ...]}
    """
    labels = {n: n for n in node_names}
    adj = {n: [] for n in node_names}
    for e in edges:
        a, b = e.get("a"), e.get("b")
        w = float(e.get("w", 1.0))
        if a in adj and b in adj and a != b:
            adj[a].append((b, w))
            adj[b].append((a, w))

    for _ in range(iters):
        changed = False
        for n in node_names:
            if not adj[n]:
                continue
            score = {}
            for m, w in adj[n]:
                score[labels[m]] = score.get(labels[m], 0.0) + w
            top = max(score.values())
            cands = sorted(l for l, s in score.items() if abs(s - top) < 1e-12)
            best = labels[n] if labels[n] in cands else cands[0]
            if best != labels[n]:
                labels[n] = best
                changed = True
        if not changed:
            break

    groups = {}
    for n, l in labels.items():
        groups.setdefault(l, []).append(n)
    for l in groups:
        groups[l].sort()
    return groups


def community_report(node_names, edges):
    """跑一次聚类并给出统计。"""
    groups = label_propagation(node_names, edges)
    # 只保留 >=2 个节点的社区，单点单独列
    big = {k: v for k, v in groups.items() if len(v) >= 2}
    singles = [v[0] for v in groups.values() if len(v) == 1]
    ordered = sorted(big.values(), key=lambda v: -len(v))
    return {
        "n_communities": len(big),
        "n_singletons": len(singles),
        "communities": ordered,
        "singletons": sorted(singles),
    }
