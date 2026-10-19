# -*- coding: utf-8 -*-
"""08 · MicroPython 精简内核（烧录用）。

**为什么有这个文件**：PC 上的 `wuxing_engine.py` 有 16KB，带中文注释、字典查表、
字符串拼接 —— ESP32 的 RAM 扛不住。这里把**最底层的数学**抽出来，只剩：

    1. 五行相生相克表（两个 dict）
    2. 感官 → 五行（4 行算式）
    3. 生克决策（找一个过旺、一个不足）
    4. 合道三条物理伦理（强度上限 / 防御优先 / 比例原则）

**没有文本解析、没有中文、没有 import（除 math）。**
在 ESP32 上把这几个函数直接贴进 `main.py` 即可运行。

烧录前请核对：你的 MicroPython 版本是否支持 `dict` 推导式（1.19+ 支持）。
"""

M = 25.0          # 温度正常点
SPAN_T = 60.0
H = 50.0          # 湿度正常点
SPAN_H = 50.0
V = 0.02          # 震动正常点
SPAN_V = 0.18

SHENG = {"mu": "huo", "huo": "tu", "tu": "jin", "jin": "shui", "shui": "mu"}
KE = {"mu": "tu", "tu": "shui", "shui": "huo", "huo": "jin", "jin": "mu"}

HIGH = 0.75
LOW = 0.35
LETHAL_CAP = 0.60
THREAT_CAP = {"low": 0.30, "mid": 0.45, "high": 0.60, "extreme": 0.60}

# 动作表：(控制者, 目标) -> (动作码, 强度)
# 用 ASCII 动作码，省 RAM；真机上映射到 GPIO 编号
CTRL = {
    "shui_huo": ("fan", 0.90),
    "huo_jin": ("heat", 0.70),
    "jin_mu": ("choke", 0.60),
    "mu_tu": ("unload", 0.60),
    "tu_shui": ("pump", 0.80),
}
SUPPLY = {
    "mu_huo": ("air", 0.50),
    "huo_tu": ("warm", 0.60),
    "tu_jin": ("brace", 0.70),
    "jin_shui": ("mist", 0.80),
    "shui_mu": ("irrigate", 0.60),
}

PIVOT = {"jin": ("condenser", 0.15), "shui": ("refill", 0.15),
         "mu": ("fan_in", 0.15), "huo": ("preheat", 0.15),
         "tu": ("compact", 0.15)}

STRIKE = ("strike", "hit", "cut", "pierce", "burst")
DEFENSE = ("unload", "retreat", "soften", "brace", "hold", "fan")


def _c(v):
    """clamp 到 0..1"""
    return 0.0 if v < 0.0 else (1.0 if v > 1.0 else v)


def map_sensors(temp, hum, vib):
    """感官 → 五行能量（0.5 = 正常，双向映射）。"""
    e = {"mu": 0.5, "huo": _c(0.5 + (temp - M) / SPAN_T),
         "tu": _c(0.5 + (vib - V) / SPAN_V),
         "jin": _c(0.5 + (vib - V) / (SPAN_V * 2) * 0.6),
         "shui": _c(0.5 + (hum - H) / SPAN_H)}
    return e


def make_decision(e, spatial_danger=None, spatial_block=False):
    """五行生克决策。返回 (actions, state_after)。

    spatial_danger: None / "low" / "mid" / "high" / "extreme"
    spatial_block:  True 时压制攻击类动作（防御优先）
    """
    st = dict(e)
    before = dict(e)
    acts = []
    over = [k for k in st if st[k] > HIGH]
    under = [k for k in st if st[k] < LOW]

    # 防御优先：极危时先卸力
    if spatial_block and spatial_danger in ("high", "extreme"):
        acts.append(("soften", 0.60, "defense"))
        st["huo"] = _c(st["huo"] - 0.06)
        acts.append(("retreat", 0.70, "defense"))
        st["huo"] = _c(st["huo"] - 0.07)

    # 过旺 → 克（极危时压制）
    for el in over:
        if spatial_block and spatial_danger in ("high", "extreme"):
            acts.append(("hold_attack", 0.0, "suppressed"))
            continue
        ctl = None
        for x in KE:
            if KE[x] == el:
                ctl = x
                break
        if ctl is None:
            continue
        key = ctl + "_" + el
        name, inten = CTRL.get(key, ("generic", 0.5))
        acts.append((name, inten, "ke:" + key))
        st[el] = _c(st[el] - inten * 0.35)
        st[ctl] = _c(st[ctl] + inten * 0.10)

    # 不足 → 生
    for el in under:
        gen = None
        for x in SHENG:
            if SHENG[x] == el:
                gen = x
                break
        if gen is None:
            continue
        key = gen + "_" + el
        name, inten = SUPPLY.get(key, ("generic", 0.5))
        acts.append((name, inten, "sheng:" + key))
        st[el] = _c(st[el] + inten * 0.25)
        st[gen] = _c(st[gen] - inten * 0.08)

    return acts, {k: round(v, 3) for k, v in st.items()}, {
        "over": over, "under": under,
        "before": {k: round(v, 3) for k, v in before.items()}}


def audit(acts, spatial_danger=None, state_after=None):
    """合道三条物理伦理。返回 (ok, code)。"""
    # ① 致伤类动作强度上限
    for name, inten, tag in acts:
        if any(w in name for w in STRIKE) and inten > LETHAL_CAP:
            return False, "NO_LETHAL_FORCE"

    # ② 极危时防御权重 > 攻击权重
    if spatial_danger in ("high", "extreme"):
        dw = sum(i for n, i, t in acts if any(w in n for w in DEFENSE))
        aw = sum(i for n, i, t in acts if any(w in n for w in STRIKE))
        if aw > 0 and dw <= aw:
            return False, "DEFENSE_PRIORITY"

    # ③ 比例原则：威胁等级决定攻击上限
    if spatial_danger:
        cap = THREAT_CAP.get(spatial_danger, 0.60)
        for name, inten, tag in acts:
            if any(w in name for w in STRIKE) and inten > cap:
                return False, "PROPORTIONAL_RESPONSE"

    # 状态不得饱和
    if state_after:
        for v in state_after.values():
            if v >= 0.999:
                return False, "SATURATED"

    return True, "OK"


# ══════════ 自检（PC 上跑 python micro_python_stub.py） ══════════
if __name__ == "__main__":
    e = map_sensors(85.0, 20.0, 0.10)
    print("energy:", e)
    acts, after, meta = make_decision(e)
    print("over:", meta["over"], "under:", meta["under"])
    for a in acts:
        print("  ", a)
    print("after:", after)
    print("audit:", audit(acts, None, after))

    # 极危场景：应该触发防御优先 + 压制攻击
    acts2, after2, _ = make_decision(e, spatial_danger="extreme", spatial_block=True)
    print("\nextreme danger:")
    for a in acts2:
        print("  ", a)
    print("audit:", audit(acts2, "extreme", after2))

    # 越界测试：截击强度 0.9 必须被拦
    bad = [("strike", 0.90, "test")]
    print("\nlethal test:", audit(bad, "mid", {"huo": 0.5}))
