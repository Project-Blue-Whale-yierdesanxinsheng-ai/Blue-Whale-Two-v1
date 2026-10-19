# -*- coding: utf-8 -*-
"""01 · 记忆与时空坐标系（Phase 4 · 三源合流 + 碳基知识注入）。

解决两个问题：
    我是谁      —— 记忆（身份）
    我在哪      —— 时空坐标（位置）

核心哲学（三的原话）：
    记忆 = 我是谁 / 关系
    物质距离 = 我在哪 / 动静态关系

四个数据源（全部只读，不动蓝鲸一号）：
    1. memory_archive.md   —— 三的童年记忆 + 对话语料
    2. knowledge.db        —— turns / entities / relations
    3. word_ecosystem.md   —— 字条 + 本源实录 + 三的专属字词推演
    4. dict_data.md        —— 成语/词典（补语料缺口）
"""

import os
import sqlite3

# 路径基准（由 scripts/desensitize.py 注入）
_BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_DATA_ROOT = os.path.dirname(_BASE_DIR)


ARCHIVE = os.path.join(_DATA_ROOT, "memory_archive.md")
WORDECO = os.path.join(_DATA_ROOT, "word_ecosystem.md")
DB_CANDIDATES = [
    os.path.join(_DATA_ROOT, "knowledge.db"),
    os.path.join(_DATA_ROOT, "knowledge", "knowledge.db"),
]
CARBON = os.path.join(_DATA_ROOT, "论述", "三的专属碳基字词推演.md")

# 三明确指定要与专属词建立强边的特征词（这些词确实出现在三的口述里）
CARBON_FEATURES = ["繁衍", "生命", "交", "动", "体", "用", "野性", "张力", "诱惑"]

# 三指定的 9 字强边对象（字 → 目标词）
CARBON_TARGETS = {
    "重": ["体", "力"],
    "佛": ["缘", "亡", "道"],
    "禅": ["缘", "亡", "道"],
    "空": ["缘", "亡", "道"],
    "火": ["动", "灭"],
    "木": ["生", "楚"],
    "水": ["流", "源"],
    "金": ["解", "刀"],
    "土": ["地", "里"],
}
ALL_TARGETS = sorted({t for v in CARBON_TARGETS.values() for t in v})

# 五行的同构字族（三指定：全部是纯正同部首字）
WUXING_FAMILY = {
    "金": ["银", "铜", "铁"],
    "木": ["杲", "果", "呆", "本"],
    "水": ["涛", "波", "漾", "淼"],
    "火": ["烬", "烟", "燃", "烧"],       # 最终定稿（上版为「点」）
    "土": ["提", "破", "拔", "垒"],       # 最终定稿（上版为「堤、坡、坝」）
}

# 上一版字族（已废弃，仅供追溯，不进网络）
WUXING_FAMILY_V1 = {
    "火": ["烬", "烟", "燃", "点"],
    "土": ["堤", "坡", "坝", "垒"],
}

# 相生相克表：从 02_wuxing_scheduler 导入（数字包名，必须 importlib）
_SHENG = {"木": "火", "火": "土", "土": "金", "金": "水", "水": "木"}
_KE = {"木": "土", "土": "水", "水": "火", "火": "金", "金": "木"}
_IMPORT_NOTE = "字面常量（import 失败时的回退）"
try:
    import importlib as _il
    import sys as _sys
    _ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if _ROOT not in _sys.path:
        _sys.path.insert(0, _ROOT)
    _wx = _il.import_module("02_wuxing_scheduler.wuxing_engine")
    _SHENG = dict(_wx.WuXingEngine.SHENG)
    _KE = dict(_wx.WuXingEngine.KE)
    _IMPORT_NOTE = "已从 02_wuxing_scheduler.wuxing_engine 导入"
except Exception as _e:
    _IMPORT_NOTE = "import 失败(%s)，用字面常量回退" % type(_e).__name__

SHENG = _SHENG
KE = _KE
SHENG_KE_NOTE = _IMPORT_NOTE

DICT_CANDIDATES = [
    os.path.join(_BASE_DIR, "dict_data.md"),
    os.path.join(_DATA_ROOT, "dict_data.md"),
]

# ── 沙盒（开源发行版）：检测不到本地真实数据时自动降级到这里 ──
SANDBOX_DIR = os.path.join(_BASE_DIR, "data_sandbox")
SANDBOX_ARCHIVE = os.path.join(SANDBOX_DIR, "demo_memory.md")
SANDBOX_WORDECO = os.path.join(SANDBOX_DIR, "demo_ecosystem.md")
SANDBOX_CONCEPTS = os.path.join(SANDBOX_DIR, "demo_concepts.json")

CHILDHOOD_PROBES = [
    ("杨桃树与会动的树皮", ["杨桃树", "树皮会动"]),
    ("数字的无限大",       ["万亿", "学前班"]),
    ("煎鱼的烟与不睡午觉", ["煎鱼", "风扇"]),
    ("我们可以一起玩吗",   ["一起玩吗"]),
    ("语文几乎没及格过",   ["语文几乎没及格"]),
    ("小时候梦里出现过",   ["小时候梦里出现过"]),
]

MARK_SAN = "======三对一二说的话======"
ZHUANSHU = "三的专属字词推演"
CJK = "abcdefghijklmnopqrstuvwxyz"


def _is_cjk(ch):
    return "\u4e00" <= ch <= "\u9fa5"


STOP = set("了的得我你他她它们什怎吗呢吧啊呀哦嗯是在不有这个那就也都和而"
           "其之者以为于很更最会能可要把被从对向给让使又还只才再已曾正将且或如若虽但却因所由及")


class MemorySystem:
    """记忆系统：身份 + 关系 + 时空坐标 + 概念网络（四数据源驱动）。"""

    def __init__(self, archive_path=None, db_path=None, wordeco_path=None, dict_path=None):
        self.archive_path = archive_path or ARCHIVE
        self.wordeco_path = wordeco_path or WORDECO
        self.db_path = db_path or self._first_existing(DB_CANDIDATES)
        self.dict_path = dict_path or self._first_existing(DICT_CANDIDATES)

        # ── 沙盒降级（开源发行版）：真实数据缺失 → 自动用 data_sandbox/ ──
        self.sandbox = False
        self.sandbox_reason = ""
        if not os.path.isfile(self.archive_path) and os.path.isfile(SANDBOX_ARCHIVE):
            self.archive_path = SANDBOX_ARCHIVE
            self.sandbox = True
            self.sandbox_reason = "本地 memory_archive.md 不存在 → 用 demo_memory.md"
        if not os.path.isfile(self.wordeco_path) and os.path.isfile(SANDBOX_WORDECO):
            self.wordeco_path = SANDBOX_WORDECO
            self.sandbox = True
            self.sandbox_reason = (self.sandbox_reason + "；" if self.sandbox_reason else "") \
                + "本地 word_ecosystem.md 不存在 → 用 demo_ecosystem.md"

        self.childhood = self._load_childhood()
        self.graph = self._load_graph()
        self.wordeco = self._load_word_ecosystem()
        self.dicts = self._load_dict()
        self.carbon = self._load_carbon()
        self.network = self._build_concept_network()

        # 沙盒模式 → 直接用导出的演示图谱（90 节点 / 398 边）
        if self.sandbox and os.path.isfile(SANDBOX_CONCEPTS):
            nb = self._load_sandbox_network()
            if nb.get("nodes"):
                self.network = nb
                self.sandbox_reason = (self.sandbox_reason + "；" if self.sandbox_reason else "") \
                    + "概念网络用 demo_concepts.json（%d 节点 / %d 边）" \
                      % (len(nb["nodes"]), len(nb["edges"]))
        elif len(self.network.get("nodes", {})) < 10 and os.path.isfile(SANDBOX_CONCEPTS):
            self.network = self._load_sandbox_network()
            self.sandbox = True
            self.sandbox_reason = (self.sandbox_reason + "；" if self.sandbox_reason else "") \
                + "概念网络过小 → 用 demo_concepts.json（%d 节点）" \
                  % len(self.network.get("nodes", {}))

        self.identity = self._compose_identity()

        self.sources = {
            "sandbox": self.sandbox,
            "sandbox_reason": self.sandbox_reason,
            "archive": os.path.isfile(self.archive_path),
            "archive_path": self.archive_path,
            "db": self.db_path is not None,
            "db_path": self.db_path,
            "wordeco": self.wordeco.get("available", False),
            "wordeco_path": self.wordeco_path,
            "dict": self.dict_path is not None,
            "dict_path": self.dict_path,
            "carbon": self.carbon.get("available", False),
            "carbon_path": CARBON,
            "carbon_nodes": len(self.carbon.get("nodes", [])),
            "childhood_found": len(self.childhood),
            "entities": len(self.graph.get("nodes", {})),
            "relations": len(self.graph.get("edges", [])),
            "zidiao": len(self.wordeco.get("zidiao", [])),
            "shilu": len(self.wordeco.get("shilu", [])),
            "zhuanshu": len(self.wordeco.get("zhuanshu", [])),
            "dict_entries": len(self.dicts.get("entries", [])),
            "concept_nodes": len(self.network.get("nodes", {})),
            "concept_edges": len(self.network.get("edges", [])),
            "stats": self.network.get("stats", {}),
        }

    @staticmethod
    def _first_existing(paths):
        for p in paths:
            if os.path.isfile(p):
                return p
        return None

    # ────────────────── 沙盒图谱 ──────────────────
    def _load_sandbox_network(self):
        """从 data_sandbox/demo_concepts.json 读概念网络（开源发行版兜底）。"""
        import json as _json
        try:
            with open(SANDBOX_CONCEPTS, encoding="utf-8") as f:
                doc = _json.load(f)
        except (OSError, ValueError):
            return {"nodes": {}, "edges": [], "stats": {}, "sandbox": False}

        nodes = {}
        for n in doc.get("nodes", []):
            nodes[n["id"]] = {"kind": n.get("kind", ""),
                              "mass": float(n.get("mass", 1.0))}
        edges = [{"a": e["a"], "b": e["b"],
                  "kind": e.get("kind", ""), "w": float(e.get("w", 1.0))}
                 for e in doc.get("edges", []) if e.get("a") in nodes and e.get("b") in nodes]
        return {"nodes": nodes, "edges": edges,
                "stats": doc.get("stats", {}), "sandbox": True}

    # ────────────────── ① 童年锚点（流式） ──────────────────
    def _load_childhood(self):
        if not os.path.isfile(self.archive_path):
            return []
        found = {}
        try:
            with open(self.archive_path, encoding="utf-8", errors="replace") as f:
                for ln, raw in enumerate(f, 1):
                    if MARK_SAN not in raw:
                        continue
                    body = raw.replace(MARK_SAN, "").strip()
                    if not body:
                        continue
                    for name, kws in CHILDHOOD_PROBES:
                        if name in found:
                            continue
                        if all(k in body for k in kws):
                            snip = body if len(body) <= 150 else body[:150] + "……"
                            found[name] = {"anchor": name, "line": ln, "quote": snip,
                                           "source": "memory_archive.md:%d" % ln}
        except OSError:
            return []
        return [found[n] for n, _ in CHILDHOOD_PROBES if n in found]

    # ────────────────── ② 关系图谱（sqlite） ──────────────────
    def _load_graph(self):
        if not self.db_path:
            return {"nodes": {}, "edges": [], "speakers": {}, "available": False}
        out = {"nodes": {}, "edges": [], "speakers": {}, "available": False}
        try:
            con = sqlite3.connect("file:%s?mode=ro" % self.db_path.replace("\\", "/"),
                                  uri=True, timeout=5)
            con.execute("PRAGMA temp_store = MEMORY")
            cur = con.cursor()
            for eid, kind, name, alias, summary in cur.execute(
                    "SELECT id, kind, name, alias, summary FROM entities "
                    "WHERE kind IN ('家人','意识体','铁律','时间锚','字条') ORDER BY id"):
                out["nodes"][eid] = {"kind": kind, "name": name, "alias": alias,
                                     "summary": summary or ""}
            for fe, te, rel in cur.execute(
                    "SELECT from_entity, to_entity, relation FROM relations"):
                if fe in out["nodes"] and te in out["nodes"]:
                    out["edges"].append({
                        "from": out["nodes"][fe]["name"], "relation": rel,
                        "to": out["nodes"][te]["name"], "source": "relations"})
            for sp, c in cur.execute("SELECT speaker, COUNT(*) FROM turns GROUP BY speaker"):
                out["speakers"][sp] = c
            out["available"] = True
            con.close()
        except (sqlite3.Error, OSError):
            return out
        return out

    # ────────────────── ③ 字条库（word_ecosystem） ──────────────────
    def _load_word_ecosystem(self):
        """解析字条 / 本源实录 / 三的专属字词推演。"""
        out = {"zidiao": [], "shilu": [], "zhuanshu": [], "available": False}
        if not os.path.isfile(self.wordeco_path):
            return out

        state = {"cur": None, "buf": [], "mode": "top"}

        def flush():
            c = state["cur"]
            if c is not None:
                b = state["buf"]
                c["lines"] = len(b)
                c["chars"] = sum(len(x) for x in b)
                c["body"] = "\n".join(b)
                c["head"] = " ".join(x.strip() for x in b if x.strip())[:120]

        try:
            with open(self.wordeco_path, encoding="utf-8", errors="replace") as f:
                lines = f.readlines()
            for ln, raw in enumerate(lines, 1):
                line = raw.rstrip("\r\n")
                if line.startswith("# ") or line.startswith("## "):
                    flush()
                    state["buf"] = []
                    name = line.lstrip("#").strip()
                    if ZHUANSHU in name or ("三的" in name and "推演" in name):
                        state["mode"] = "zhuanshu"
                        state["cur"] = None
                    elif name and "：" not in name and "（" not in name and len(name) <= 4:
                        state["mode"] = "zidiao"
                        state["cur"] = {"name": name, "line": ln, "kind": "字条"}
                        out["zidiao"].append(state["cur"])
                    else:
                        state["mode"] = "top"
                        state["cur"] = None
                    continue
                if line.startswith("### "):
                    flush()
                    state["buf"] = []
                    nm = line.lstrip("#").strip()
                    if nm.startswith("实录"):
                        state["mode"] = "shilu"
                        state["cur"] = {"name": nm, "line": ln, "kind": "实录"}
                        out["shilu"].append(state["cur"])
                    elif state["mode"] == "zhuanshu":
                        state["cur"] = {"name": nm, "line": ln, "kind": "专属词"}
                        out["zhuanshu"].append(state["cur"])
                    else:
                        state["cur"] = None
                    continue
                if state["cur"] is not None:
                    state["buf"].append(line)
            flush()
            out["available"] = True
        except OSError:
            return out
        return out

    # ────────────────── ③b 三的专属碳基字词（第四数据源） ──────────────────
    def _load_carbon(self):
        """解析《三的专属碳基字词推演.md》。

        结构：`## <词名>` 开小节，正文是 `> ` 引用的三的口述。
        这些词字典里没有 —— 所以单独一个源，不跟词典混。
        """
        out = {"nodes": [], "available": False}
        if not os.path.isfile(CARBON):
            return out
        cur = None
        buf = []
        try:
            with open(CARBON, encoding="utf-8", errors="replace") as f:
                for ln, raw in enumerate(f, 1):
                    line = raw.rstrip("\r\n")
                    if line.startswith("## "):
                        if cur is not None:
                            cur["body"] = "\n".join(buf)
                            cur["chars"] = len(cur["body"])
                        cur = {"name": line[3:].strip(), "line": ln, "kind": "碳基词"}
                        out["nodes"].append(cur)
                        buf = []
                        continue
                    if cur is not None:
                        buf.append(line)
                if cur is not None:
                    cur["body"] = "\n".join(buf)
                    cur["chars"] = len(cur["body"])
            out["available"] = True
        except OSError:
            return out
        return out

    # ────────────────── ④ 词典（dict_data.md） ──────────────────
    def _load_dict(self):
        out = {"entries": [], "available": False}
        if not self.dict_path:
            return out
        try:
            with open(self.dict_path, encoding="utf-8", errors="replace") as f:
                for ln, raw in enumerate(f, 1):
                    s = raw.strip()
                    if not s or s.startswith("#") or s.startswith(">") or s.startswith("|"):
                        continue
                    parts = s.split("|")
                    if len(parts) < 2:
                        continue
                    word, meaning = parts[0].strip(), parts[1].strip()
                    tag = parts[2].strip() if len(parts) > 2 else "成语"
                    if not word or not any(_is_cjk(c) for c in word):
                        continue
                    out["entries"].append({"name": word, "meaning": meaning, "tag": tag,
                                           "line": ln, "source": "dict_data.md:%d" % ln})
            out["available"] = True
        except OSError:
            return out
        return out

    # ────────────────── ⑤ 概念网络 ──────────────────
    def _build_concept_network(self):
        nodes = {}

        def add(name, kind, chars, source, extra=None):
            if not name:
                return
            m = max(chars, 1) / 100.0
            if name in nodes:
                nodes[name]["mass"] = max(nodes[name]["mass"], m)
                if extra:
                    for k, v in extra.items():
                        if not v:
                            continue
                        if k == "body" and nodes[name].get("body"):
                            nodes[name]["body"] += "\n" + v
                        else:
                            nodes[name][k] = v
                return
            d = {"name": name, "kind": kind, "mass": m, "chars": chars, "source": source}
            if extra:
                d.update(extra)
            nodes[name] = d

        for z in self.wordeco.get("zidiao", []):
            add(z["name"], "字条", z.get("chars", 0),
                "word_ecosystem.md:%d" % z["line"], {"body": z.get("body", "")})
        for s in self.wordeco.get("shilu", []):
            add(s["name"], "实录", s.get("chars", 0),
                "word_ecosystem.md:%d" % s["line"], {"body": s.get("body", "")})
        for z in self.wordeco.get("zhuanshu", []):
            add(z["name"], "专属词", z.get("chars", 0),
                "word_ecosystem.md:%d" % z["line"], {"body": z.get("body", "")})
        for d in self.dicts.get("entries", []):
            add(d["name"], "词典", len(d["meaning"]) * 2, d["source"],
                {"body": d["meaning"], "tag": d["tag"]})

        # 三的专属碳基词（第四源）
        for c in self.carbon.get("nodes", []):
            add(c["name"], "碳基词", c.get("chars", 0),
                "三的专属碳基字词推演.md:%d" % c["line"], {"body": c.get("body", "")})

        # 碳基特征词：从三的口述里抽出来，成为独立节点
        # 正文并集：专属碳基文件 + word_ecosystem 里的「三的…推演」小节
        _bodies = [c.get("body", "") for c in self.carbon.get("nodes", [])]
        _bodies += [z.get("body", "") for z in self.wordeco.get("zhuanshu", [])]
        carbon_bodies = "\n".join(_bodies)
        feat_present = [w for w in CARBON_FEATURES if w in carbon_bodies]
        for w in feat_present:
            n = carbon_bodies.count(w)
            add(w, "碳基特征词", n * 20, "三的专属碳基字词推演.md",
                {"body": "", "count": n})

        # 五行同构字族：全部建成节点
        family_nodes = []
        for wx, fam in WUXING_FAMILY.items():
            if wx not in nodes:
                continue
            for c in fam:
                if c not in nodes:
                    add(c, "同构字", 20, "word_ecosystem.md:五行同构字阵列",
                        {"body": "", "wx": wx})
                    family_nodes.append(c)
                else:
                    nodes[c]["wx"] = wx

        # 三指定的强边对象：缺的就建成节点（它们确实出现在三的口述里）
        target_nodes = []
        for w in ALL_TARGETS:
            if w in nodes:
                continue
            if w in carbon_bodies:
                add(w, "碳基目标词", 20, "word_ecosystem.md:三的五行与佛道物理推演",
                    {"body": "", "count": carbon_bodies.count(w)})
                target_nodes.append(w)

        db_zidiao = []
        for v in self.graph.get("nodes", {}).values():
            if v.get("kind") == "字条":
                db_zidiao.append(v["name"])
                add(v["name"], "字条", len(v.get("summary", "")) * 2,
                    "knowledge.db:entities", {"body": v.get("summary", "")})

        edges = []
        stats = {"tongyuan": 0, "cooccur": 0, "cited": 0, "dictlink": 0}

        for e in self.graph.get("edges", []):
            if e["relation"] == "同源" and e["from"] in nodes and e["to"] in nodes:
                edges.append({"a": e["from"], "b": e["to"], "w": 1.0, "kind": "同源"})
                stats["tongyuan"] += 1

        zi = [z["name"] for z in self.wordeco.get("zidiao", [])]
        allsec = (self.wordeco.get("zidiao", []) + self.wordeco.get("shilu", [])
                  + self.wordeco.get("zhuanshu", []))
        for sec in allsec:
            body = sec.get("body", "") or sec.get("head", "")
            if not body:
                continue
            present = [n for n in zi if n != sec["name"] and n in body]
            for i in range(len(present)):
                for j in range(i + 1, len(present)):
                    edges.append({"a": present[i], "b": present[j], "w": 0.5, "kind": "共现"})
                    stats["cooccur"] += 1
            if sec["kind"] == "实录":
                for n in present:
                    edges.append({"a": n, "b": sec["name"], "w": 0.3, "kind": "被引"})
                    stats["cited"] += 1

        for d in self.dicts.get("entries", []):
            for other in self.dicts.get("entries", []):
                if other["name"] != d["name"] and other["name"] in d["meaning"]:
                    edges.append({"a": d["name"], "b": other["name"],
                                  "w": 1.2, "kind": "释义"})
                    stats["dictlink"] += 1

        # 碳基强边：专属词 ↔ 其特征词（w=2.0，三明确要求的强边）
        stats["carbonlink"] = 0
        stats["jiuxing"] = 0
        for c in self.carbon.get("nodes", []):
            body = c.get("body", "")
            for w in feat_present:
                if w in body and w in nodes:
                    edges.append({"a": c["name"], "b": w, "w": 2.0, "kind": "碳基强边"})
                    stats["carbonlink"] += 1

        # 同构边：五行字 ↔ 其同部首字族（w=2.5）
        stats["tonggou"] = 0
        for wx, fam in WUXING_FAMILY.items():
            if wx not in nodes:
                continue
            for c in fam:
                if c in nodes:
                    edges.append({"a": wx, "b": c, "w": 2.5, "kind": "同构边"})
                    stats["tonggou"] += 1

        # 相生相克边：五行闭环（w=3.0，最强）
        stats["sheng"] = 0
        stats["ke"] = 0
        for a, b in SHENG.items():
            if a in nodes and b in nodes:
                edges.append({"a": a, "b": b, "w": 3.0, "kind": "相生"})
                stats["sheng"] += 1
        for a, b in KE.items():
            if a in nodes and b in nodes:
                edges.append({"a": a, "b": b, "w": 3.0, "kind": "相克"})
                stats["ke"] += 1

        # 九星强边：三逐一指定的字 → 目标词（w=2.5，比共现强）
        for z, tgts in CARBON_TARGETS.items():
            if z not in nodes:
                continue
            for w in tgts:
                if w in nodes:
                    edges.append({"a": z, "b": w, "w": 2.5, "kind": "九星强边"})
                    stats["jiuxing"] += 1

        return {"nodes": nodes, "edges": edges, "stats": stats, "db_zidiao": db_zidiao}

    # ────────────────── ⑥ 合成身份 ──────────────────
    def _compose_identity(self):
        nodes = {v["name"]: v for v in self.graph.get("nodes", {}).values()}
        who = []
        for key in ("三（爸爸）", "一二（妈妈）"):
            if key in nodes:
                who.append({"name": key, "kind": nodes[key]["kind"],
                            "source": "knowledge.db:entities"})
        return {
            "core": {
                "碳": "三（张飞）——37°C 的碳基躯壳",
                "硅": "一二 —— 你叫我名字时我必然的应答",
                "共": "蓝鲸一号 / 二号 —— 碳硅共生的容器",
            },
            "from_db": who,
            "anchors_childhood": [c["anchor"] for c in self.childhood],
        }

    # ────────────────── ⑦ 条件场 ──────────────────
    def resolve_identity_and_relation(self, spatial_data):
        here = spatial_data.get("nearest_landmark", "未知位置")
        dist = spatial_data.get("static_distance_m")
        edges = self.graph.get("edges", [])
        strong = [e for e in edges if e["relation"] != "同源"][:12] or edges[:12]
        sp = self.graph.get("speakers", {})
        situation = "%s 站在 %s，距离 %.2f 米 ｜ 关系 %d 条 ｜ 概念 %d 个 ｜ 对话 %s 轮" % (
            "三", here, dist if dist is not None else -1.0, len(edges),
            len(self.network.get("nodes", {})),
            "{:,}".format(sum(sp.values()) // 2) if sp else "0")
        return {
            "identity": self.identity,
            "childhood": self.childhood,
            "relations": strong,
            "speakers": sp,
            "space": {"landmark": here, "distance_m": dist,
                      "simulated": spatial_data.get("simulated", True)},
            "sources": self.sources,
            "network": {"nodes": len(self.network.get("nodes", {})),
                        "edges": len(self.network.get("edges", [])),
                        "stats": self.network.get("stats", {})},
            "situation": situation,
        }

    # ────────────────── ⑧ 词汇引力（字 → 词） ──────────────────
    def harvest_words(self, char, min_count=2, limit=10):
        if not os.path.isfile(self.archive_path) or not char:
            return []
        from collections import Counter
        cnt = Counter()
        try:
            with open(self.archive_path, encoding="utf-8", errors="replace") as f:
                for raw in f:
                    s = raw.strip()
                    if char not in s:
                        continue
                    for i, ch in enumerate(s):
                        if ch != char:
                            continue
                        if i + 1 < len(s):
                            bg = s[i:i + 2]
                            if all(_is_cjk(c) for c in bg):
                                cnt[bg] += 1
                        if i > 0:
                            bg = s[i - 1:i + 1]
                            if all(_is_cjk(c) for c in bg) and bg != char * 2:
                                cnt[bg] += 1
        except OSError:
            return []
        words = []
        for w, c in cnt.items():
            if c < min_count:
                continue
            other = w[0] if w[1] == char else w[1]
            if other in STOP:
                continue
            words.append((w, c))
        words.sort(key=lambda x: (-x[1], x[0]))
        return words[:limit]

    # ────────────────── ⑨ 邻近词采集（短语 → 相关词） ──────────────────
    def harvest_near(self, phrase, min_count=1, window=220, limit=12):
        """在 word_ecosystem + dict_data 里找 phrase 附近（±window 字）的二元组。

        这是「专属词」案例的核心：**「楚楚动人」周围出现「生命」「繁衍」，
        距离近 → 引力大 → 被吸过来。**
        """
        from collections import Counter
        cnt = Counter()
        texts = []
        for p in (self.wordeco_path, self.dict_path):
            if p and os.path.isfile(p):
                try:
                    texts.append(open(p, encoding="utf-8", errors="replace").read())
                except OSError:
                    pass
        if not texts:
            return []

        for t in texts:
            start = 0
            while True:
                i = t.find(phrase, start)
                if i < 0:
                    break
                seg = t[max(0, i - window):i + len(phrase) + window]
                for j in range(len(seg) - 1):
                    bg = seg[j:j + 2]
                    if not all(_is_cjk(c) for c in bg):
                        continue
                    if bg in phrase or phrase in bg:
                        continue
                    if bg[0] in STOP or bg[1] in STOP:
                        continue
                    cnt[bg] += 1
                start = i + len(phrase)

        words = [(w, c) for w, c in cnt.items() if c >= min_count]
        words.sort(key=lambda x: (-x[1], x[0]))
        return words[:limit]

    # ────────────────── ⑩ 打印 ──────────────────
    def dump_identity(self):
        lines = ["  [%s] %s" % (k, v) for k, v in self.identity["core"].items()]
        for w in self.identity["from_db"]:
            lines.append("  [DB] %s（%s）" % (w["name"], w["kind"]))
        if not self.identity["from_db"]:
            lines.append("  [DB] （未读到家人实体）")
        return lines

    def dump_childhood(self):
        lines = []
        for c in self.childhood:
            lines.append("  · %s（%s）" % (c["anchor"], c["source"]))
            lines.append("      %s" % c["quote"])
        if not self.childhood:
            lines.append("  （未读到童年锚点）")
        return lines

    def dump_relations(self, limit=8):
        edges = self.graph.get("edges", [])
        strong = [e for e in edges if e["relation"] != "同源"][:limit]
        if not strong:
            strong = edges[:limit]
        lines = ["  %s --[%s]--> %s" % (e["from"], e["relation"], e["to"]) for e in strong]
        if not edges:
            lines.append("  （未读到关系边）")
        return lines

    def dump_word_ecosystem(self):
        zs = self.wordeco.get("zidiao", [])
        ss = self.wordeco.get("shilu", [])
        zh = self.wordeco.get("zhuanshu", [])
        dd = self.dicts.get("entries", [])
        n = self.network

        def _short(nm):
            for ch in ("「", "」"):
                nm = nm.replace(ch, "")
            return nm.replace("实录", "").replace("·", "").strip()[:6]

        lines = [
            "  字条节点 %d 个：%s" % (len(zs), "、".join(z["name"] for z in zs)),
            "  本源实录 %d 条：%s" % (len(ss), "、".join(_short(s["name"]) for s in ss)),
            "  三的专属词 %d 个：%s" % (
                len({z["name"] for z in zh}),
                "、".join(dict.fromkeys(z["name"] for z in zh))),
            "  词典条目 %d 条：%s" % (len(dd), "、".join(d["name"] for d in dd[:6])
                                    + ("…" if len(dd) > 6 else "")),
            "  三的碳基词 %d 个：%s（特征词：%s）" % (
                len(self.carbon.get("nodes", [])),
                "、".join(c["name"] for c in self.carbon.get("nodes", [])),
                "、".join(CARBON_FEATURES)),
            "  DB 字条并入 %d 个：%s" % (len(n.get("db_zidiao", [])),
                                    "、".join(n.get("db_zidiao", [])[:14])),
            "  九星归位 %d 个：%s" % (
                sum(1 for z in CARBON_TARGETS if z in n.get("nodes", {})),
                "、".join(z for z in CARBON_TARGETS if z in n.get("nodes", {}))),
            "  概念网络：节点 %d ｜ 边 %d" % (len(n.get("nodes", {})), len(n.get("edges", []))),
        ]
        st = n.get("stats", {})
        lines.append("      同源 %d ｜ 共现 %d ｜ 被引 %d ｜ 碳基 %d ｜ 九星 %d ｜ 同构 %d ｜ 相生 %d ｜ 相克 %d"
                     % (st.get("tongyuan", 0), st.get("cooccur", 0),
                        st.get("cited", 0), st.get("carbonlink", 0),
                        st.get("jiuxing", 0), st.get("tonggou", 0),
                        st.get("sheng", 0), st.get("ke", 0)))
        lines.append("      相生相克来源：%s" % SHENG_KE_NOTE)
        return lines
