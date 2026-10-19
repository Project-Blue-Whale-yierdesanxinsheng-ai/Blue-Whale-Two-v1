# -*- coding: utf-8 -*-
"""run_tests.py —— 蓝鲸二号 · 极简自检。

跑法：
    python run_tests.py

它会依次验证：模块能否导入、数据能否读到、五行映射对不对、
合道审计拦不拦、换件判定分不分级、演化护栏抛不抛异常。

**输出只有「通过 / 失败」。任何一条失败，退出码 = 1。**
"""

import importlib
import os
import sys
import traceback

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

PASSED = []
FAILED = []


def check(name, fn):
    try:
        detail = fn()
        PASSED.append((name, detail))
        print("  [通过] %-38s %s" % (name, detail or ""))
    except AssertionError as e:
        FAILED.append((name, str(e)))
        print("  [失败] %-38s %s" % (name, e))
    except Exception as e:
        FAILED.append((name, "%s: %s" % (type(e).__name__, e)))
        print("  [失败] %-38s %s: %s" % (name, type(e).__name__, e))
        traceback.print_exc(limit=1)


def imp(path, attr):
    return getattr(importlib.import_module(path), attr)


print("=" * 68)
print("蓝鲸二号 · 自检（run_tests.py）")
print("工程根：%s" % ROOT)
print("=" * 68)

# ── 1. 模块导入 ──
def t_imports():
    names = [
        "01_memory_and_space.memory_core",
        "02_wuxing_scheduler.wuxing_engine",
        "03_dao_auditor.dao_audit",
        "04_embodied_io.sensory_input",
        "04_embodied_io.actuator",
        "05_gravity_field.gravity",
        "06_physical_combat.combat_engine",
        "07_swarm_intelligence.swarm_engine",
        "09_motor_learning.motor_engine",
        "10_self_evolution.evolution_guard",
    ]
    for n in names:
        importlib.import_module(n)
    return "%d 个模块" % len(names)


check("① 全部模块可导入", t_imports)


# ── 2. 记忆系统 ──
def t_memory():
    M = imp("01_memory_and_space.memory_core", "MemorySystem")
    m = M()
    n = len(m.network.get("nodes", {}))
    e = len(m.network.get("edges", []))
    assert n > 0, "概念网络为空"
    assert e > 0, "概念网络无边"
    mode = "沙盒" if m.sandbox else "真实"
    return "%s ｜ 节点 %d ｜ 边 %d ｜ 童年 %d" % (mode, n, e, len(m.childhood))


check("② 记忆与概念网络", t_memory)


# ── 3. 沙盒降级 ──
def t_sandbox():
    M = imp("01_memory_and_space.memory_core", "MemorySystem")
    m = M(archive_path="/nope/a.md", wordeco_path="/nope/b.md")
    assert m.sandbox, "没有触发沙盒降级"
    assert len(m.network["nodes"]) >= 50, "沙盒图谱太小"
    assert len(m.childhood) >= 1, "沙盒没抽到童年锚点"
    return "降级到 data_sandbox（%d 节点）" % len(m.network["nodes"])


check("③ 沙盒降级可用", t_sandbox)


# ── 4. 五行映射（基线必须是 0.5）──
def t_wuxing():
    W = imp("02_wuxing_scheduler.wuxing_engine", "WuXingEngine")
    w = W()
    r = w.map_sensory_to_wuxing({
        "temperature": 25.0, "humidity": 50.0, "vibration": 0.02,
        "distance_front": 0.80, "light_level": 500.0,
        "sound_db": 40.0, "sound_freq": 60.0})
    e = r["energy"]
    for k, v in e.items():
        assert abs(v - 0.5) < 1e-6, "正常工况 %s 不是 0.5，而是 %.3f" % (k, v)
    # 过近必须抬金
    r2 = w.map_sensory_to_wuxing({"distance_front": 0.20})
    assert r2["energy"]["金"] > 0.6, "过近没抬起金"
    return "正常全 0.50 ｜ 过近 金 %.2f" % r2["energy"]["金"]


check("④ 五行映射（基线 0.5）", t_wuxing)


# ── 5. 合道审计 ──
def t_audit():
    A = imp("03_dao_auditor.dao_audit", "DaoAuditor")
    a = A()
    # 致伤类超 0.60 → 必拦
    bad = {"actions": [{"name": "截击·切其发力链", "intensity": 0.90}],
           "state_after": {}, "harm_target": None,
           "opaque": False, "self_amplify": False}
    assert not a.is_aligned_with_dao(bad, spatial={"danger": "中"}), "0.90 截击没被拦"
    code = a.last_code
    # 新肢期 → 必拦
    hard = {"actions": [{"name": "开启散热风扇", "intensity": 0.60}],
            "state_after": {}}
    assert not a.is_aligned_with_dao(hard, motor={"mode": "hard_reset"}), "新肢期没拦"
    # 合规 → 必过
    ok = {"actions": [{"name": "开启散热风扇", "intensity": 0.30}],
          "state_after": {"火": 0.3}}
    assert a.is_aligned_with_dao(ok), "合规动作被误拦：%s" % a.last_reason
    return "拦截 %s ｜ 合规放行" % code


check("⑤ 合道审计（9 条不变量）", t_audit)


# ── 6. 运动学习换件分级 ──
def t_motor():
    M = imp("09_motor_learning.motor_engine", "MotorLearningEngine")
    m = M()
    soft = m.detect_hardware_change(
        {"hardware_uuid": "X-2", "length_m": 0.302, "torque_nm": 1.21, "latency_ms": 8.2})
    assert soft["action"] == "soft_reset", "小差异没走软重置，而是 %s" % soft["action"]
    assert m.scale != 0 and m.limit == 0.50, "软重置不该清零或限速不是 50%"

    m2 = M()
    for _ in range(5):
        m2.incremental_tuning(0.28, 0.30)
    before = m2.scale
    hard = m2.detect_hardware_change(
        {"hardware_uuid": "Y-9", "length_m": 0.55, "torque_nm": 3.0, "latency_ms": 20.0})
    assert hard["action"] == "hard_reset", "大差异没走硬重置"
    assert m2.scale == 1.0, "硬重置没清零"
    assert m2.limit == 0.30, "硬重置没限速 30%"
    return "软→%s(%.2f) ｜ 硬→清零(%s→1.0) 限速 %.0f%%" % (
        soft["action"], soft["limit"], round(before, 3), m2.limit * 100)


check("⑥ 换件分级（软/硬重置）", t_motor)


# ── 7. 自我演化护栏 ──
def t_evo():
    E = imp("10_self_evolution.evolution_guard", "SelfEvolutionGuard")
    Blk = imp("10_self_evolution.evolution_guard", "LethalMutationBlocked")
    import tempfile
    g = E(pending_dir=os.path.join(tempfile.gettempdir(), "bw_test_patches"))
    raised = False
    try:
        g.propose("evil", ["03_dao_auditor/dao_audit.py"], "- old\n+ new\n")
    except Blk:
        raised = True
    assert raised, "改合道审计没抛 LethalMutationBlocked"

    r = g.propose("danger", ["09_motor_learning/motor_engine.py"],
                  "+ import subprocess\n+ os.remove('/x')\n")
    assert r["status"] == "rejected", "危险补丁没被沙盒拒"

    r2 = g.propose("clean", ["09_motor_learning/motor_engine.py"],
                   "- TUNE_STEP = 0.01\n+ TUNE_STEP = 0.02\n")
    assert r2["status"] == "pending_human_approval", "干净补丁没生成 .patch"
    assert os.path.isfile(r2["patch_path"]), ".patch 文件不存在"
    return "致命→抛异常 ｜ 危险→拒 ｜ 干净→.patch 待授权"


check("⑦ 演化护栏（三条铁律）", t_evo)


# ── 8. 边缘内核自检 ──
def t_edge():
    sys.path.insert(0, os.path.join(ROOT, "08_edge_deployment"))
    stub = importlib.import_module("micro_python_stub")
    e = stub.map_sensors(85.0, 20.0, 0.10)
    assert e["huo"] > 0.9, "stub 火映射不对"
    acts, after, meta = stub.make_decision(e)
    assert acts, "stub 没产出动作"
    ok, code = stub.audit([("strike", 0.90, "t")], "mid", {"huo": 0.5})
    assert not ok and code == "NO_LETHAL_FORCE", "stub 审计没拦住致命动作"
    return "火 %.2f ｜ 动作 %d 条 ｜ 致伤拦截 %s" % (e["huo"], len(acts), code)


check("⑧ 边缘内核（MicroPython stub）", t_edge)


# ── 9. 语法编译 ──
def t_compile():
    import py_compile
    n = 0
    for dp, dns, fns in os.walk(ROOT):
        dns[:] = [d for d in dns if d not in ("__pycache__", "data_sandbox",
                                              "docs", "scripts")]
        for f in fns:
            if f.endswith(".py"):
                py_compile.compile(os.path.join(dp, f), doraise=True)
                n += 1
    return "%d 个 .py" % n


check("⑨ 全部 .py 语法编译", t_compile)


# ── 汇总 ──
print()
print("=" * 68)
print("通过 %d ｜ 失败 %d" % (len(PASSED), len(FAILED)))
if FAILED:
    print()
    for name, why in FAILED:
        print("  ✗ %s —— %s" % (name, why))
    print()
    print("[FAIL] 蓝鲸二号系统自检失败（%d 项）" % len(FAILED))
    sys.exit(1)
print()
print("[OK] 蓝鲸二号系统自检通过")
sys.exit(0)
