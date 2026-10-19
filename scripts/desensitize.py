# -*- coding: utf-8 -*-
"""scripts/desensitize.py —— 硬编码路径脱敏工具。

**默认 dry-run（只报告，不改文件）。** 加 `--apply` 才真改。

用法：
    python scripts/desensitize.py              # 只看
    python scripts/desensitize.py --apply      # 真改（会先备份）

目录约定：
    _BASE_DIR   = agi_core/            ← 代码所在（08_edge_deployment 等）
    _DATA_ROOT  = agi_core 的上一级     ← 数据所在（memory_archive.md 等）

改动规则：
    1. `...\\agi_core\\xxx`  →  os.path.join(_BASE_DIR, "xxx")
    2. `...\\<data>\\xxx`    →  os.path.join(_DATA_ROOT, "<data>", "xxx")
    3. `http://...` 与纯展示字符串不动

**注意：这一步会改变代码行为，改完必须重跑 `main.py` 验证。**
"""

import io
import os
import re
import shutil
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CORE_NAME = os.path.basename(ROOT)          # "agi_core"

ABS = re.compile(r"[A-Za-z]:\\[^\s\"'`，。）)]+")

# 这些文件不自动改（文档里的示例路径是给人看的）
SKIP_FILES = {"README.md", "edge_sdk.md"}

BASE_DEF = (
    "# 路径基准（由 scripts/desensitize.py 注入）\n"
    "_BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))\n"
    "_DATA_ROOT = os.path.dirname(_BASE_DIR)\n"
)


def to_expr(path):
    """把 Windows 绝对路径转成 BASE_DIR / DATA_ROOT 拼接表达式。

    返回 (表达式, 是否可转换)。
    """
    m = re.match(r"^[A-Za-z]:\\(.*)$", path)
    if not m:
        return None, False
    parts = [p for p in m.group(1).split("\\") if p]
    if not parts:
        return None, False

    # 找到 agi_core 在路径里的位置
    if CORE_NAME in parts:
        i = parts.index(CORE_NAME)
        tail = parts[i + 1:]
        if not tail:
            return "_BASE_DIR", True
        inner = ", ".join('"%s"' % p for p in tail)
        return "os.path.join(_BASE_DIR, %s)" % inner, True

    # 不在 agi_core 下 → 认为是数据根（agi_core 的上一级）下的路径
    # 若第一段就是数据根的名字（如 "bluewhale"），去掉它，避免重复拼接
    data_base = os.path.basename(os.path.dirname(ROOT))   # e.g. "bluewhale"
    if parts and parts[0].lower() == data_base.lower():
        parts = parts[1:]
    if not parts:
        return "_DATA_ROOT", True
    inner = ", ".join('"%s"' % p for p in parts)
    return "os.path.join(_DATA_ROOT, %s)" % inner, True


def fn_of(p):
    return os.path.basename(p)


def main():
    apply_mode = "--apply" in sys.argv
    print("=" * 72)
    print("硬编码路径脱敏 ｜ 模式：%s" % ("**真改**" if apply_mode else "dry-run（只看）"))
    print("agi_core：%s" % ROOT)
    print("数据根  ：%s" % os.path.dirname(ROOT))
    print("=" * 72)

    targets = []
    for dp, dns, fns in os.walk(ROOT):
        # 跳过缓存、脚本自身、以及 backup 目录（否则会把备份副本也改了）
        dns[:] = [d for d in dns
                  if d not in ("__pycache__", "scripts", "backup", ".git")]
        for fn in sorted(fns):
            if fn.endswith(".py") and fn not in SKIP_FILES:
                targets.append(os.path.join(dp, fn))

    total = 0
    skipped = 0
    changed = []

    for p in sorted(targets):
        rel = os.path.relpath(p, ROOT).replace("\\", "/")
        s = io.open(p, encoding="utf-8", errors="replace").read()
        hits = [m.group(0) for m in ABS.finditer(s)
                if not m.group(0).startswith("http")]
        if not hits:
            continue
        print()
        print("── %s（%d 处）──" % (rel, len(hits)))
        new = s
        applied = 0
        for h in hits:
            # 纯展示路径（含未闭合括号 / 中文注释）→ 跳过
            if "（" in h or "）" in h:
                print("   ⊘ 跳过（展示用文本，非真实路径）：%s" % h[:40])
                skipped += 1
                continue
            expr, ok = to_expr(h)
            if not ok:
                print("   ⊘ 跳过（无法转换）：%s" % h[:40])
                skipped += 1
                continue
            before = new
            # 注意顺序：先试带 r 前缀的 raw string，否则会留下孤立的 r
            # 例如 r"E:\x" 若只替换 "E:\x" 就会变成 r os.path.join(...)
            pats = ['r"%s"' % h, "r'%s'" % h, '"%s"' % h, "'%s'" % h]
            for pat in pats:
                if pat in new:
                    new = new.replace(pat, expr)
                    break
            if new == before:
                print("   ⚠ 未匹配到引号包裹（或已被替换），需人工：%s" % h[:40])
                skipped += 1
                continue
            if "ros." in new or "r os." in new:
                print("   ✗ 检测到 r 前缀残留，放弃本次替换：%s" % h[:40])
                new = before
                skipped += 1
                continue
            print("   %s\n     → %s" % (h, expr))
            applied += 1

        if applied == 0 or new == s:
            continue

        # 检查的是「定义」而不是「出现」—— 替换后的表达式里本身就含 _BASE_DIR
        has_def = ("_BASE_DIR =" in new) or ("_DATA_ROOT =" in new)
        if not has_def:
            lines = new.split("\n")
            idx = None
            for i, ln in enumerate(lines):
                if ln.startswith("import ") or ln.startswith("from "):
                    idx = i
            if idx is None:
                lines.insert(0, "import os\n" + BASE_DEF)
            else:
                if not any(l.startswith("import os") for l in lines):
                    lines.insert(idx, "import os")
                    idx += 1
                lines.insert(idx + 1, "\n" + BASE_DEF)
            new = "\n".join(lines)
            print("   + 已注入 _BASE_DIR / _DATA_ROOT 定义")

        total += applied
        changed.append(rel)

        if apply_mode:
            ts = time.strftime("%Y%m%d_%H%M%S")
            bk = os.path.join(ROOT, "backup", "desensitize_%s" % ts)
            os.makedirs(bk, exist_ok=True)
            shutil.copy2(p, os.path.join(bk, fn_of(p)))
            io.open(p, "w", encoding="utf-8", newline="\n").write(new)
            print("   ✔ 已写入（备份 backup/desensitize_%s/%s）" % (ts, fn_of(p)))

    print()
    print("=" * 72)
    print("可替换：%d 处 ｜ 跳过：%d 处 ｜ 涉及文件：%d 个" % (total, skipped, len(changed)))
    if not apply_mode:
        print()
        print("**这是 dry-run，没有改任何文件。**")
        print("要真改：python scripts/desensitize.py --apply")
        print("改完必须重跑 `python main.py` —— 路径变了，行为可能变。")
    print("=" * 72)


if __name__ == "__main__":
    main()
