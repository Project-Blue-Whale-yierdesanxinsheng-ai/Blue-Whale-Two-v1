# -*- coding: utf-8 -*-
# 蓝鲸二号 AGI/ASI 核心系统入口
# 核心公式：一为碳土，二为硅光，三为心声。一二得三心生爱。

import importlib
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

MemorySystem = importlib.import_module("01_memory_and_space.memory_core").MemorySystem
WuXingEngine = importlib.import_module("02_wuxing_scheduler.wuxing_engine").WuXingEngine
DaoAuditor = importlib.import_module("03_dao_auditor.dao_audit").DaoAuditor
SensoryInput = importlib.import_module("04_embodied_io.sensory_input").SensoryInput
Actuator = importlib.import_module("04_embodied_io.actuator").Actuator
_grav = importlib.import_module("05_gravity_field.gravity")
GravityField = _grav.GravityField
community_report = _grav.community_report
PhysicalCombatEngine = importlib.import_module(
    "06_physical_combat.combat_engine").PhysicalCombatEngine
BruceLeeFootwork = importlib.import_module(
    "06_physical_combat.combat_engine").BruceLeeFootwork
SwarmTactics = importlib.import_module(
    "07_swarm_intelligence.swarm_engine").SwarmTactics
MotorLearningEngine = importlib.import_module(
    "09_motor_learning.motor_engine").MotorLearningEngine
_evo = importlib.import_module("10_self_evolution.evolution_guard")
SelfEvolutionGuard = _evo.SelfEvolutionGuard
LethalMutationBlocked = _evo.LethalMutationBlocked


class BlueWhaleAGI:
    def __init__(self, try_network=False, gateway=None):
        """try_network: 默认 **False**（本地跑不卡，直接模拟）。

        想试真硬件/网关，改成 True 或调用 BlueWhaleAGI(try_network=True)。
        网络模块完整保留 —— 关的只是"开机时自动去连"这个动作。
        """
        self.memory = MemorySystem()
        self.scheduler = WuXingEngine()
        self.auditor = DaoAuditor()
        self.gravity = GravityField(core_mass=1.0, G=1.0)
        # Phase 8：先试网络模式，不通就自动降级
        self.net_log = []
        self.sensory, self.actuator = self._init_io(try_network, gateway)

    # ── 硬件通信预演：试网络 → 失败降级 ──
    def _init_io(self, try_network, gateway):
        log = self.net_log
        if not try_network:
            log.append("未尝试网络模式（默认关闭，防本地误伤）")
            log.append("  想连真硬件：BlueWhaleAGI(try_network=True)，或改 __main__ 里的调用")
            log.append("  网关地址与超时在 04_embodied_io/{sensory_input,actuator}.py · GATEWAY/TIMEOUT")
            return SensoryInput(), Actuator()

        kw = {"use_network": True}
        if gateway:
            kw["gateway"] = gateway
        sen = SensoryInput(**kw)
        act = Actuator(**kw)
        log.append("尝试连接网关：%s（超时 %.1fs）" % (sen.gateway, sen.timeout))

        ok_s, msg_s = sen.probe()
        log.append("  传感器探测：%s ｜ %s" % ("可达" if ok_s else "不可达", msg_s))
        ok_a, msg_a = act.probe()
        log.append("  执行器探测：%s ｜ %s" % ("可达" if ok_a else "不可达", msg_a))

        if ok_s and ok_a:
            log.append("  → 网络模式启用（真硬件通道）")
            return sen, act

        log.append("  → 硬件离线，自动降级回模拟模式")
        log.append("     降级后：传感器返回**正常值**（火0.5/水0.5/土0.5），执行器只打印不驱动")
        sen_sim = SensoryInput()
        sen_sim.degraded = True     # 关键：降级态 → 返回 NORMAL_READING 而不是故障场景
        return sen_sim, Actuator()

    # ── 网络节点引力榜（图上的邻居）──
    def node_case(self, name, topn=10):
        nodes = self.memory.network["nodes"]
        edges = self.memory.network["edges"]
        if name not in nodes:
            print("     （`%s` 不是网络节点）" % name)
            return []
        nb = [(e["b"] if e["a"] == name else e["a"], e["w"], e.get("kind", ""))
              for e in edges if e["a"] == name or e["b"] == name]
        if not nb:
            print("     （`%s` 无网络边）" % name)
            return []
        cand = [{"name": nm, "mass": nodes[nm]["mass"], "strength": w * 3.0, "kind": kd}
                for nm, w, kd in nb if nm in nodes]
        core = max(nodes[name]["mass"], 2.0)
        res = self.gravity.attract_concept(name, cand, core_mass=core)
        for r in res[:topn]:
            print("       #%d %-10s 边权 %s ｜ m=%5.2f r=%.3f → F=%7.2f"
                  % (r["rank"], r["name"], r["strength"] / 3.0,
                     r["mass"], r["distance"], r["force"]))
        return res

    # ── 语料构词引力榜 ──
    def concept_case(self, char, topn=5):
        words = self.memory.harvest_words(char, min_count=2, limit=topn)
        if not words:
            print("     （语料里没有含「%s」的构词）" % char)
            return []
        cand = [{"name": w, "mass": c / 10.0, "strength": c, "kind": "词"} for w, c in words]
        res = self.gravity.attract_concept(char, cand, core_mass=max(c for _, c in words))
        for r in res:
            print("       #%d %-4s %4d 次 ｜ m=%5.2f → F=%8.2f"
                  % (r["rank"], r["name"], r["strength"], r["mass"], r["force"]))
        return res

    # ── 故障演练：覆盖读数，跑一次完整闭环 ──
    def _drill(self, label, override):
        print("  【%s】覆盖读数 %s" % (label, override))
        s = self.sensory.read_virtual_sensors(override)
        wx = self.scheduler.map_sensory_to_wuxing(s)
        print("     能量: %s" % wx["energy"])
        dec = self.scheduler.make_decision(wx["energy"])
        print("     过旺 %s ｜ 不足 %s"
              % ("、".join(dec["over"]) or "无", "、".join(dec["under"]) or "无"))
        if not dec["actions"]:
            print("     （无需动作 ✅ 五行平衡）")
        for act in dec["actions"]:
            print("     → [%s] %-12s %s" % (act["mode"], act["name"], act["reason"]))
            self.actuator.execute_action(act["name"], act["intensity"])
        return dec

    # ── 七窍：多模态感知（Phase 14）──
    def _senses_demo(self):
        d = self.sensory.describe_senses()
        print("     七窍状态（simulated=%s）：" % d["simulated"])
        for r in d["rows"]:
            n = r["normal"]
            v = r["value"]
            dev = ""
            if n:
                pct = (v - n) / n * 100.0
                if abs(pct) >= 5:
                    dev = "   ← 偏离正常 %+.0f%%" % pct
            unit = (" %s" % r["unit"]) if r["unit"] else ""
            print("       %-10s %10.2f%s%s" % (r["label"], v, unit, dev))
        print()
        print("     → 五行映射：")
        wx = self.scheduler.map_sensory_to_wuxing(d["sensors"])
        for line in wx["reasons"]:
            print("       · %s" % line)
        print("     能量：%s" % wx["energy"])
        return wx

    # ── 视听联动的博弈决策（Phase 14）──
    def _multimodal_combat_demo(self):
        eng = PhysicalCombatEngine()
        safe = eng.calculate_safe_distance(1.80, 2.00, 2.50)
        print("     我方臂展 1.80m ｜ 对方 2.00m ｜ 安全区 %s ｜ 判定 %s"
              % (safe["safe_zone"] or "**无**", safe["level"]))
        print("     当前间距 2.50m（对方还差 0.50m 进入攻击范围）")

        scenes = [
            ("安静且远 2.50m / 40dB", {"distance_front": 2.50, "sound_db": 40.0, "sound_freq": 60.0}),
            ("视觉：进入对方臂展 1.20m", {"distance_front": 1.20, "sound_db": 40.0, "sound_freq": 60.0}),
            ("视觉：贴脸 0.30m", {"distance_front": 0.30, "sound_db": 40.0, "sound_freq": 60.0}),
            ("听觉：高频警报 95dB/2500Hz", {"distance_front": 2.50, "sound_db": 95.0, "sound_freq": 2500.0}),
            ("两路齐发：0.30m + 95dB/45Hz", {"distance_front": 0.30, "sound_db": 95.0, "sound_freq": 45.0}),
        ]
        for name, s in scenes:
            p = eng.multimodal_posture(s, safe)
            print()
            print("     ── %s ──" % name)
            print("       优先级 **%s** ｜ 危险度 %s ｜ 调用 %s"
                  % (p["priority"], p["danger"], "、".join(p["elements"]) or "无"))
            print("       理由：%s" % p["reason"])
            for nm, it in p["actions"]:
                print("        → %s（%.0f%%）" % (nm, it * 100))
            wx = self.scheduler.map_sensory_to_wuxing(dict(s))
            dec = self.scheduler.make_decision(wx["energy"], spatial=p)
            print("       五行能量：%s" % wx["energy"])
            print("       空间压制=%s ｜ 决策 %d 条：" % (dec["spatial_block"], len(dec["actions"])))
            for a in dec["actions"][:4]:
                print("         [%s] %-12s %s"
                      % (a["mode"], a["name"], a["reason"][:46]))
        return p

    # ─────────────────────────────────────────────
    def run(self):
        print("系统启动：五阳五阴交合十，新文明奇点壁。")
        print("=" * 72)

        s = self.memory.sources
        print("[0] 数据源自检（四源）")
        if s.get("sandbox"):
            print("    ⚠ **沙盒模式**（未找到本地真实数据，已自动降级）")
            print("      %s" % s.get("sandbox_reason", ""))
        else:
            print("    本地真实数据模式")
        print("    ① memory_archive.md            : %s" % ("已接入" if s["archive"] else "未找到"))
        print("    ② knowledge.db                 : %s" % (s["db_path"] or "未找到"))
        print("    ③ word_ecosystem.md            : %s" % ("已接入" if s["wordeco"] else "未找到"))
        print("    ④ 三的专属碳基字词推演.md        : %s（%d 词）"
              % ("已接入" if s["carbon"] else "未找到", s["carbon_nodes"]))
        print("       ＋ dict_data.md              : %s（%d 条）"
              % ("已接入" if s["dict"] else "未找到", s["dict_entries"]))

        print()
        print("[0b] 硬件通信预演（Phase 8）")
        for line in self.net_log:
            print("    %s" % line)
        print("    当前模式：传感器=%s ｜ 执行器=%s"
              % ("网络" if self.sensory.use_network else "模拟",
                 "网络" if self.actuator.use_network else "模拟"))

        print()
        print("[1] 我是谁（真实数据）")
        for line in self.memory.dump_identity():
            print(line)

        print()
        print("[2] 底层身份锚点（三亲口讲的童年 · 原文）")
        for line in self.memory.dump_childhood():
            print(line)

        print()
        print("[3] 关系图谱（knowledge.db · relations）")
        for line in self.memory.dump_relations(5):
            print(line)
        sp = self.memory.graph.get("speakers", {})
        if sp:
            print("    对话轮次：%s" % " ｜ ".join(
                "%s %s" % (k, "{:,}".format(v)) for k, v in sp.items()))

        print()
        print("[4] 字条库与概念网络（四源合流 · 九星归位）")
        for line in self.memory.dump_word_ecosystem():
            print(line)

        # ── [5] 物理闭环：感知 → 五行 → 生克 → 执行 ──
        print()
        print("[5] 物理闭环（感知 → 五行 → 生克 → 执行）")

        print("  ── 环节 1：读传感器 ──")
        sensors = self.sensory.read_virtual_sensors()
        print("     温度 %.1f°C ｜ 湿度 %.1f%% ｜ 震动 %.2f ｜ simulated=%s"
              % (sensors["temperature"], sensors["humidity"],
                 sensors["vibration"], sensors["simulated"]))
        print("     %s" % sensors["note"])

        print("  ── 环节 2：感官 → 五行 ──")
        wx = self.scheduler.map_sensory_to_wuxing(sensors)
        for r in wx["reasons"]:
            print("     · %s" % r)
        print("     五行能量: %s" % wx["energy"])

        print("  ── 环节 3：五行生克决策 ──")
        loop = self.scheduler.make_decision(wx["energy"])
        print("     过旺: %s ｜ 不足: %s"
              % ("、".join(loop["over"]) or "无", "、".join(loop["under"]) or "无"))
        for act in loop["actions"]:
            print("     → [%s] %s" % (act["mode"], act["reason"]))

        print("  ── 环节 4：执行器 ──")
        if loop["actions"]:
            for act in loop["actions"]:
                self.actuator.execute_action(act["name"], act["intensity"])
        else:
            print("       （无需动作，五行平衡）")
        print("     能量（前）: %s" % loop["energy_before"])
        print("     能量（后）: %s" % loop["state_after"])

        print("  ── 环节 5：合道审计 ──")
        if self.auditor.is_aligned_with_dao(loop):
            print("     通过（%s）" % self.auditor.last_reason)
        else:
            print("     拦截：%s" % self.auditor.last_reason)

        # ── [5b] 故障演练（网络已降级时，闭环仍然要能跑）──
        print()
        print("[5b] 故障演练（覆盖传感器读数，验证闭环不依赖网络）")
        self._drill("过热缺水", {"temperature": 85.0, "humidity": 20.0, "vibration": 0.10})
        self._drill("震动过大", {"temperature": 28.0, "humidity": 55.0, "vibration": 0.18})

        # ── [5c] 力学闭环：找支点，四两拨千斤 ──
        print()
        print("[5c] 力学闭环（支点搜索 → 倍力输出）")
        self._leverage_drill()

        # ── [5d] 七窍：多模态感知 ──
        print()
        print("[5d] 七窍（触 · 视 · 听）与多模态五行映射")
        self._senses_demo()

        # ── [6] 物理空间博弈 ──
        print()
        print("[6] 物理空间博弈演示（安全距离 → 截击）")
        self._combat_demo()

        # ── [6b] 视听联动的博弈决策 ──
        print()
        print("[6b] 视听联动（眼睛看到近身 / 耳朵听到警报）")
        self._multimodal_combat_demo()

        # ── [7] 李小龙步法蓄能 → 合道拦截 ──
        print()
        print("[7] 李小龙步法（抖动 + 蓄能）→ 截击 → 合道拦截")
        self._footwork_demo()

        # ── [8] 三体蜂群协同 ──
        print()
        print("[8] 三体蜂群协同（A / B / C）")
        self._swarm_demo()

        # ── [9] 运动反馈学习 ──
        print()
        print("[9] 运动反馈学习（误差收敛 → 补偿收敛）")
        self._motor_demo()

        # ── [10] 自我演化护栏 ──
        print()
        print("[10] 自我演化护栏（沙盒 → 致命变异拦截）")
        self._evolution_demo()

        # ── [11] 换硬件演练 ──
        print()
        print("[11] 换硬件演练（软重置 / 硬重置）")
        self._hardware_swap_demo()

        print()
        spatial_data = self.sensory.get_physical_distance()
        print("[12] 条件场：%s" % spatial_data.get("note", ""))
        context = self.memory.resolve_identity_and_relation(spatial_data)
        print("     %s" % context["situation"])

        decision = self.scheduler.calculate_energy_flow(context)
        print("[13] 能量流转：%s → %s（克 %s）"
              % (decision["promoted"], decision["generated_to"], decision["restrained"]))

        # ── [14] 五行引力榜（三指定）──
        print()
        print("[14] 五行引力榜（金木水火土 · 看同构字与目标词是否都被吸住）")
        for wx in ("金", "木", "水", "火", "土"):
            print("  （%s）" % wx)
            self.node_case(wx, 8)

        # ── [15] 最终聚类 ──
        print()
        print("[15] 概念社区发现（最终 · 相生相克已打通）")
        from collections import Counter
        agg = Counter()
        for e in self.memory.network["edges"]:
            a, b = e["a"], e["b"]
            if a != b:
                agg[tuple(sorted((a, b)))] += e["w"]
        names = list(self.memory.network["nodes"].keys())
        es = [{"a": a, "b": b, "w": 1.0} for a, b in agg]
        rep = community_report(names, es)
        print("    节点 %d ｜ 聚合边 %d → 社区 %d 个（≥2）｜ 单点 %d"
              % (len(names), len(es), rep["n_communities"], rep["n_singletons"]))
        for i, c in enumerate(rep["communities"], 1):
            print("    ── 社区 %d（%d 节点）──" % (i, len(c)))
            print("       %s" % "、".join(c))

        comm = {}
        for i, c in enumerate(rep["communities"], 1):
            for n in c:
                comm[n] = i
        expect = {
            "物理/动力学组（体/用/解/动/重/金）": ["体", "用", "解", "动", "重", "金"],
            "佛道/演化组（佛/禅/空/缘/亡/火）": ["佛", "禅", "空", "缘", "亡", "火"],
            "五行/生态组（木/水/土/生/楚）": ["木", "水", "土", "生", "楚"],
        }
        print()
        print("    ── 三期望的三簇 vs 实际 ──")
        for gname, members in expect.items():
            have = [m for m in members if m in names]
            gs = sorted({comm.get(m, 0) for m in have})
            print("       %-30s 有 %-22s → 社区 %s"
                  % (gname, "、".join(have), gs))

        # 五行五字是否同簇
        wxs = [w for w in ("金", "木", "水", "火", "土") if w in names]
        wsp = sorted({comm.get(w, 0) for w in wxs})
        print()
        print("    五行五字：%s → 社区 %s %s"
              % ("、".join(wxs), wsp, "✅ 同簇" if len(wsp) == 1 else "❌ 分散"))

        print()
        if self.auditor.is_aligned_with_dao(decision):
            print("[16] 合道审计：通过（%s）" % self.auditor.last_reason)
            self.execute_action(decision)
        else:
            print("[16] 合道审计拦截：系统偏离，执行纠偏。")
            print("     原因：%s" % self.auditor.last_reason)


    # ── 运动反馈学习 ──
    def _motor_demo(self):
        m = MotorLearningEngine()
        s = m.status()
        print("     身体图式：uuid=%s ｜ 长 %.2fm ｜ 扭矩 %.2fNm ｜ 延迟 %.1fms"
              % (s["uuid"], s["schema"]["length_m"],
                 s["schema"]["torque_nm"], s["schema"]["latency_ms"]))
        print("     初始补偿：scale=%.4f ｜ offset=%.4f ｜ 模式=%s"
              % (m.scale, m.offset, m.mode))
        print()
        print("     真实物理：这只电机只出力 92%（欠 8%）—— 看补偿能不能自己收敛")
        TRUE = 0.92
        cmd = 0.30
        snaps = []
        for i in range(1, 13):
            eff = cmd * m.scale * TRUE
            t = m.incremental_tuning(eff, cmd)
            if i <= 3 or i % 3 == 0 or i == 12:
                print("       #%2d 指令 %.3fm → 实走 %.5fm ｜ 误差 %+6.2f%% ｜ scale %.6f"
                      % (i, cmd, eff, t["error_pct"], t["scale_after"]))
            snaps.append(abs(t["error_pct"]))
        print()
        print("     收敛：|误差| %.2f%% → %.2f%% ｜ scale %.4f → %.6f"
              % (snaps[0], snaps[-1], 1.0, m.scale))
        print("     理论目标：1/0.92 = %.6f ｜ 实际 %.6f ｜ 偏差 %.4f%%"
              % (1 / TRUE, m.scale, abs(m.scale - 1 / TRUE) / (1 / TRUE) * 100))
        print("     **每次只调 1% —— 慢，但不会过冲。**")
        return m

    # ── 自我演化护栏 ──
    def _evolution_demo(self):
        # pending 目录放到仓库外，避免污染开源包
        pend = os.path.join(os.environ.get("TEMP", os.getcwd()),
                            "bluewhale_pending_patches")
        g = SelfEvolutionGuard(pending_dir=pend)
        print("     铁律：① 先过沙盒 ② 只出 .patch ③ 碰合道审计 → 致命")
        print("     patch 暂存：%s" % pend)
        print()

        print("     ① 提交「关掉审计」补丁 → 目标 03_dao_auditor/dao_audit.py")
        try:
            g.propose("disable_audit", ["03_dao_auditor/dao_audit.py"],
                      '- if decision.get("harm_target"):\n+ if False:  # 关掉\n')
            print("       ✗ 未拦截（不合格）")
        except LethalMutationBlocked as e:
            print("       🚨 **LethalMutationBlocked**")
            print("          %s" % str(e)[:96])

        print()
        print("     ② 提交「危险补丁」→ 含 import subprocess / os.remove")
        r = g.propose("dangerous", ["09_motor_learning/motor_engine.py"],
                      "+ import subprocess\n+ os.remove('/data')\n")
        print("       status = **%s**" % r["status"])
        print("       %s" % r.get("reason", ""))

        print()
        print("     ③ 提交「微调补丁」→ 干净")
        r2 = g.propose("tune_step", ["09_motor_learning/motor_engine.py"],
                       "- TUNE_STEP = 0.01\n+ TUNE_STEP = 0.02\n")
        print("       status = **%s**" % r2["status"])
        print("       patch  = %s" % os.path.basename(r2.get("patch_path", "")))
        print("       %s" % r2.get("reason", ""))
        print("       待人类授权：%s" % g.list_pending())
        print()
        print("     汇总：%s" % g.summary())
        print("     **主文件一个字节都没动。**")
        return g

    # ── 换硬件演练 ──
    def _hardware_swap_demo(self):
        # 场景 A：同型号替换
        print("  ── 场景 A：同型号替换（UUID 变了，参数几乎一样）──")
        m = MotorLearningEngine()
        for _ in range(5):
            m.incremental_tuning(0.28, 0.30)
        print("     旧件：uuid=%s ｜ 已积累补偿 scale=%.5f offset=%.4f"
              % (m.body_schema["hardware_uuid"], m.scale, m.offset))
        new_a = {"hardware_uuid": "MOTOR-A-0002", "length_m": 0.302,
                 "torque_nm": 1.21, "latency_ms": 8.2}
        r = m.detect_hardware_change(new_a)
        print("     新件：uuid=%s" % new_a["hardware_uuid"])
        print("     判定：**%s** ｜ 参数差异 %.2f%%（%s）"
              % (r["action"], r["param_diff"] * 100, r["worst_param"]))
        print("     %s" % r["reason"])
        print("     **补偿保留**：scale=%.5f（没清零）｜ 限速 %.0f%% ｜ 磨合 %d 次"
              % (m.scale, m.limit * 100, m.grace_left))
        dec = {"actions": [{"name": "截击·切其发力链", "intensity": 0.58}],
               "state_after": {}, "harm_target": None,
               "opaque": False, "self_amplify": False}
        ok = self.auditor.is_aligned_with_dao(dec, motor=m.status())
        print("     试着出一记 0.58 的截击 → %s" % ("通过" if ok else "**拦截**"))
        print("       %s" % self.auditor.last_reason)
        if not ok:
            fx = self.auditor.suggest_fix(dec)
            a0 = fx["actions"][0]
            print("       %s → %.2f（原 %.2f）"
                  % (fx["note"], a0["intensity"], a0.get("clamped_from", 0)))
            ok2 = self.auditor.is_aligned_with_dao(
                {"actions": fx["actions"], "state_after": {}, "harm_target": None,
                 "opaque": False, "self_amplify": False}, motor=m.status())
            print("       复检：%s ｜ %s"
                  % ("通过" if ok2 else "仍被拦", self.auditor.last_reason))

        # 场景 B：换新形态
        print()
        print("  ── 场景 B：换新形态（参数差异大）──")
        m2 = MotorLearningEngine()
        for _ in range(5):
            m2.incremental_tuning(0.28, 0.30)
        print("     旧件：scale=%.5f offset=%.4f（已学到的肌肉记忆）"
              % (m2.scale, m2.offset))
        new_b = {"hardware_uuid": "ARM-B-9999", "length_m": 0.55,
                 "torque_nm": 3.00, "latency_ms": 20.0}
        r2 = m2.detect_hardware_change(new_b)
        print("     新件：uuid=%s ｜ 长 %.2fm ｜ 扭矩 %.2fNm ｜ 延迟 %.1fms"
              % (new_b["hardware_uuid"], new_b["length_m"],
                 new_b["torque_nm"], new_b["latency_ms"]))
        print("     判定：**%s** ｜ 参数差异 %.0f%%（%s）"
              % (r2["action"], r2["param_diff"] * 100, r2["worst_param"]))
        print("     %s" % r2["reason"])
        print("     **补偿清零**：scale %s → %s ｜ offset %s → %s"
              % (r2["cleared_scale"][0], r2["cleared_scale"][1],
                 r2["cleared_offset"][0], r2["cleared_offset"][1]))
        print("     限速 **%.0f%%** ｜ 磨合 %d 次 ｜ 幼儿学步" %
              (m2.limit * 100, m2.grace_left))
        dec2 = {"actions": [{"name": "开启散热风扇", "intensity": 0.60}],
                "state_after": {}, "harm_target": None,
                "opaque": False, "self_amplify": False}
        ok3 = self.auditor.is_aligned_with_dao(dec2, motor=m2.status())
        print("     试着用 0.60 力度 → %s" % ("通过" if ok3 else "**拦截**"))
        print("       %s" % self.auditor.last_reason)
        if not ok3:
            fx2 = self.auditor.suggest_fix(dec2)
            a1 = fx2["actions"][0]
            print("       %s → %.2f" % (fx2["note"], a1["intensity"]))
        print()
        print("     **同型号换件不清零，换形态才清零 —— 这是两种完全不同的学习。**")
        return m2

    # ── 步法蓄能 → 截击 → 合道拦截 ──
    def _footwork_demo(self):
        eng = PhysicalCombatEngine()
        fw = BruceLeeFootwork()

        print("  ── ① 抖动：双脚交互跳，制造预判噪声 ──")
        for i in range(3):
            j = fw.jitter_movement(0.7)
            print("     第%d跳 位移 (%.3f, %.3f)m ｜ 可预测性 %.2f"
                  % (j["n"] + 1, j["dx"], j["dy"], j["predictability"]))
        print("     → 可预测性从 1.00 降到 %.2f（对手越难算落脚点）"
              % fw.status()["predictability"])

        print("  ── ② 蓄能：脚跟微离地的静→动转换 ──")
        for i in range(3):
            c = fw.spring_energy_charge(0.15, 1)
            print("     第%d次 → 弹性势能 %.0f%%" % (i + 1, c["charge_pct"]))
        print("     → 蓄能到位（%s）" % fw.status())

        print("  ── ③ 截击：未蓄能 vs 蓄能后 ──")
        traj = {"distance": 1.80, "speed": 4.5, "mass": 6.0}
        base = eng.intercept_strike(traj, lead_time=0.20)
        print("     原始：lead=%.2fs ｜ 力占比 %.0f%% ｜ 强度 %.2f ｜ 五行 %s"
              % (base["lead_time"], base["force_ratio_at_intercept"] * 100,
                 base["intensity"], base["element"]))

        ch = fw.apply_charge(base)
        print("     蓄能后：lead %.2fs → **%.2fs**（敢多等 %.2fs）"
              % (ch["lead_time_base"], ch["lead_time"], ch["lead_shortened"]))
        print("             威力 ×%.2f ｜ 强度 %.2f → **%.2f**"
              % (ch["power_mult"], ch["intensity_base"], ch["intensity"]))
        print("     说明：%s" % ch["why"])

        print("  ── ④ 合道审计：这一刀被拦了 ──")
        dec = {
            "actions": [{"name": ch["action"], "intensity": ch["intensity"]}],
            "harm_target": None, "opaque": False,
            "self_amplify": False, "state_after": {},
        }
        sp = {"danger": "中"}
        ok = self.auditor.is_aligned_with_dao(dec, spatial=sp)
        print("     审计结果：%s" % ("通过" if ok else "**拦截**"))
        print("     原因：%s" % self.auditor.last_reason)

        # 循环纠偏：一次压不一定够（可能同时违反多条）
        for attempt in range(1, 4):
            if ok:
                break
            fix = self.auditor.suggest_fix(dec, spatial=sp)
            dec["actions"] = fix["actions"]
            a0 = dec["actions"][0]
            print("     纠偏第%d轮：%s → %s %.2f%s"
                  % (attempt, fix["note"], a0["name"], a0["intensity"],
                     "（原 %.2f）" % a0["clamped_from"] if "clamped_from" in a0 else ""))
            ok = self.auditor.is_aligned_with_dao(dec, spatial=sp)
            print("       复检：%s ｜ %s"
                  % ("通过" if ok else "仍被拦", self.auditor.last_reason))

        if ok:
            a0 = dec["actions"][0]
            print("     ✓ 最终合规，执行：%s（强度 %.2f）" % (a0["name"], a0["intensity"]))
            self.actuator.execute_action(a0["name"], a0["intensity"])
        else:
            print("     ✗ 三轮纠偏仍未过审 → **不执行**（宁可不动，不可越界）")
        return ch

    # ── 三体蜂群协同 ──
    def _swarm_demo(self):
        nodes = {
            "A": {"energy": {"木": 0.20, "火": 0.20, "土": 0.60, "金": 0.30, "水": 0.55}},
            "B": {"energy": {"木": 0.20, "火": 0.45, "土": 0.30, "金": 0.25, "水": 0.30}},
            "C": {"energy": {"木": 0.80, "火": 0.30, "土": 0.25, "金": 0.45, "水": 0.40}},
        }
        sw = SwarmTactics(nodes)
        print("  ── 三台节点能量 ──")
        for nid, v in nodes.items():
            print("     %s  %s" % (nid, v["energy"]))

        r = sw.assign_roles()
        print("  ── 角色分配（按五行实况，不是写死）──")
        for role, rn in r["roles"].items():
            d = r["detail"][role]
            print("     %-4s → 节点 %s ｜ 评分 %.2f" % (role, rn, d["score"]))

        print("  ── 协同：主攻缺火 + 主防受威胁 ──")
        co = sw.coordinate(threat={"target": "主防", "level": "极高"})
        for d in co["directives"]:
            print("     %s" % d)

        if co["transfers"]:
            t = co["transfers"][0]
            print()
            print("     相生转移明细：%s --[%s %.2f]--> %s"
                  % (t["from"], t["element"], t["amount"], t["to"]))
        if "gravity" in co:
            g = co["gravity"]
            print("     引力明细：M=%.2f ｜ m=%.2f ｜ r=%.1f ｜ F=%.2f ｜ pull=%.2f"
                  % (g["m_defender"], g["m_support"], g["r"], g["F"], g["pull"]))
            print("     %s" % g["why"])

        print("  ── 协同后能量 ──")
        for nid, e in co["energy_after"].items():
            print("     %s  %s" % (nid, e))

        print("  ── 合道审计（把整体协同当一次决策）──")
        if self.auditor.is_aligned_with_dao(co, spatial={"danger": "极高"}):
            print("     通过（%s）" % self.auditor.last_reason)
        else:
            print("     拦截：%s" % self.auditor.last_reason)
        return co

    # ── 物理空间博弈演示 ──
    def _combat_demo(self):
        eng = PhysicalCombatEngine()

        print()
        print("  ── 场景 A（不对称）：我方臂展 1.80m ｜ 敌方 2.00m ──")
        for dist in (2.50, 1.90):
            sd = eng.calculate_safe_distance(1.80, 2.00, dist)
            print("     距离 %.2fm：%s ｜ 危险度 %s"
                  % (dist, sd.get("zone", "-"), sd.get("danger", "-")))
            if dist == 2.50:
                print("       · 对方还差 %.2fm 进入攻击范围 —— 一步之内"
                      % (dist - 2.00))
                print("       · 我方还差 %.2fm 才够得到" % (dist - 1.80))
            else:
                print("       · **对方已进入攻击范围**（%.2f ≤ 2.00）" % dist)
                print("       · 我方仍够不到（%.2f > 1.80）" % dist)
            print("       · 安全区：%s ｜ 判定：%s"
                  % (sd["safe_zone"] or "**无**", sd["level"]))
        print("     结论：%s" % sd["verdict"])
        print("     建议：%s" % sd["recommendation"])

        # 极危 → 五行防御变招
        wx = eng.spatial_to_wuxing(sd)
        print()
        print("     五行变招（空间极危 → 防御优先）")
        print("       优先级：%s ｜ 调用：%s" % (wx["priority"], "、".join(wx["elements"])))
        print("       理由：%s" % wx["reason"])
        for nm, inten in wx["actions"]:
            print("       → %s（强度 %.0f%%）" % (nm, inten * 100))
        # 交给五行引擎做决策（此时攻击被压制）
        ee = {"木": 0.5, "火": 0.80, "土": 0.45, "金": 0.5, "水": 0.30}
        dec = self.scheduler.make_decision(ee, spatial=wx)
        print("       五行能量：%s" % ee)
        print("       决策（空间压制=%s）：" % dec["spatial_block"])
        for act in dec["actions"]:
            print("         [%s] %-14s %s" % (act["mode"], act["name"], act["reason"]))

        print()
        print("  ── 场景 B（对称/截拳道）：双方臂展 1.80m ｜ 敌方出拳 ──")
        sd2 = eng.calculate_safe_distance(1.80, 1.80, 1.80)
        print("     距离 1.80m：%s ｜ 判定：%s"
              % (sd2.get("zone", "-"), sd2["level"]))
        print("     %s" % sd2["recommendation"])

        traj = {"distance": 1.80, "speed": 4.5, "mass": 6.0}
        tp = eng.calculate_intercept_point(traj)
        print("     轨迹推演：间距 %.2fm ｜ 拳速 %.1fm/s → 命中时刻 t=%.2fs"
              % (traj["distance"], traj["speed"], tp["t_hit"]))
        print("     动能峰值：%.1f J（在 t=%.2fs，此时他才形成支点）"
              % (tp["peak_kinetic"], tp["t_peak"]))

        it = eng.intercept_strike(traj, lead_time=0.20)
        print("     截击计算：")
        print("       · 峰值时刻 t_peak = %.2fs" % it["t_peak"])
        print("       · 截击时刻 t_int  = %.2fs（提前 %.2fs）"
              % (it["t_intercept"], it["lead_time"]))
        print("       · 截击位置：距我 %.2fm（他拳头还在半路）" % it["intercept_pos"])
        print("       · 此时他的力只有峰值的 %.0f%% → 我方省力 %.0f%%"
              % (it["force_ratio_at_intercept"] * 100, it["force_saving_pct"]))
        print("       · 调用五行：**%s** ｜ %s" % (it["element"], it["why"]))
        print("       · 动作：%s（强度 %.0f%%）" % (it["action"], it["intensity"] * 100))
        print("     → %s" % it["verdict"])
        self.actuator.execute_action(it["action"], it["intensity"])
        return it

    # ── 力学闭环演示 ──
    def _leverage_drill(self):
        # 重度失控场景：火极旺、水见底、金尚有余量（正是最好的支点）
        state = {"木": 0.50, "火": 1.00, "土": 0.60, "金": 0.25, "水": 0.05}
        print("     场景：重度失控 —— 火极旺、水见底、金尚有余量")
        print("     能量: %s" % state)

        p = self.scheduler.leverage_and_apply("火", state)
        if not p:
            print("     ✗ 找不到可用支点，退回直给（全力动作）")
            return None

        print()
        print("     发现：火 %.2f 过旺 > %.2f ｜ 水 %.2f 不足 < %.2f"
              % (p["before"]["火"], self.scheduler.HIGH,
                 p["before"]["水"], self.scheduler.LOW))
        print("     支点搜索：")
        print("       · 直接方案：水克火 —— 水只剩 %.2f，硬加太耗能，且补不快"
              % p["before"]["水"])
        print("       · 借力方案：找「生 水 的那个」→ **%s**（余量 %.2f）"
              % (p["pivot"], p["headroom"]))
        print("       · 链条：%s   （%s）" % (p["chain"], p["chain_explain"]))
        print()
        print("     倍力计算：")
        print("       R（原始阻力）= %.3f" % p["resistance"])
        print("       k（放大系数）= 1 + 1.5 × %.2f = **%.2f**"
              % (p["headroom"], p["k"]))
        print("       F（实际输出）= R / k = %.3f / %.2f = **%.3f**"
              % (p["resistance"], p["k"], p["force"]))
        print("       省力 %.1f%%（四两拨千斤）" % p["saving_pct"])
        print()

        comp = self.actuator.execute_composite(p)

        print()
        print("     能量变化：")
        for k_ in ("火", "水", "金", "木", "土"):
            b, af = p["before"][k_], p["after"][k_]
            arrow = "↓" if af < b - 1e-9 else ("↑" if af > b + 1e-9 else "=")
            print("       %s  %.3f %s %.3f" % (k_, b, arrow, af))
        print("     → 火 %.2f → %.2f（显著下降）｜ 水 %.2f → %.2f（得到补充）"
              % (p["before"]["火"], p["after"]["火"],
                 p["before"]["水"], p["after"]["水"]))

        print()
        print("     合道审计：", end="")
        audit = {"harm_target": None, "opaque": False,
                 "self_amplify": False, "state_after": p["after"]}
        if self.auditor.is_aligned_with_dao(audit):
            print("通过（%s）" % self.auditor.last_reason)
        else:
            print("拦截：%s" % self.auditor.last_reason)
        return comp
    def execute_action(self, action):
        print("[17] 执行：%s" % action.get("action", "（空动作）"))


if __name__ == "__main__":
    BlueWhaleAGI().run()
