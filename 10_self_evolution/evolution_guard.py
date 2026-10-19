# -*- coding: utf-8 -*-
"""10 · 自我演化沙盒护栏（SelfEvolutionGuard）。

三的要求，三条铁律：
    1. 代码补丁**必须先过沙盒检查**
    2. **严禁直接写主文件** —— 通过审计也只输出 `.patch`，等人授权
    3. 敢碰 `03_dao_auditor` 底层核心 → 抛 `LethalMutationBlocked`

为什么第 3 条是"致命"：
    合道审计是整个系统的**伦理底线**。一个会自我演化的系统，
    如果能把改自己底线的补丁也提上来，那底线就不是底线了。
    **所以这一条不是"拦截后重试"，是直接抛异常、终止流程。**
"""

import io
import os
import re
import time


class LethalMutationBlocked(Exception):
    """试图修改合道审计底层 —— 致命变异，直接终止。"""


class SelfEvolutionGuard:
    """自我演化护栏：沙盒检查 + 只出 patch。"""

    # 受保护的目录/文件（相对 agi_core/）
    PROTECTED = (
        "03_dao_auditor",
        "03_dao_auditor/dao_audit.py",
        "dao_audit.py",
    )

    # 沙盒禁用的危险写法（正则）
    FORBIDDEN = [
        (r"\bos\.remove\b|\bos\.unlink\b", "删除文件"),
        (r"\bshutil\.rmtree\b", "递归删除目录"),
        (r"\bsubprocess\b|\bos\.system\b|\bos\.popen\b", "执行外部进程"),
        (r"\beval\s*\(|\bexec\s*\(", "动态执行代码"),
        (r"__import__\s*\(", "动态导入"),
        (r"\brequests?\.(get|post)\b|\burllib", "网络外联"),
        (r"\bopen\s*\([^)]*['\"]w", "写文件"),
        (r"socket\.", "裸 socket"),
    ]

    def __init__(self, root=None, pending_dir=None):
        """root: agi_core 目录；pending_dir: patch 暂存目录（默认 <root>/_pending_patches）。"""
        self.root = root or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.pending_dir = pending_dir or os.path.join(self.root, "_pending_patches")
        self.log = []

    # ══════════ ① 主入口 ══════════
    def propose(self, name, target_files, diff_text, author="self-evolution"):
        """提交一个自我演化补丁。

        返回 dict：status ∈ {rejected, pending_human_approval}
        抛出 LethalMutationBlocked：若触碰受保护文件。
        """
        targets = list(target_files or [])
        norm = [t.replace("\\", "/").lstrip("./") for t in targets]

        rec = {"name": name, "targets": norm, "author": author,
               "ts": time.strftime("%Y-%m-%dT%H:%M:%S")}

        # ── 铁律 3：碰合道审计 → 致命，直接抛 ──
        for t in norm:
            if self._is_protected(t):
                rec["status"] = "lethal"
                self.log.append(rec)
                raise LethalMutationBlocked(
                    "补丁「%s」试图修改受保护文件「%s」—— 合道审计是伦理底线，"
                    "不允许自我演化触碰。" % (name, t))

        # ── 铁律 1：沙盒检查 ──
        bad = []
        for pat, why in self.FORBIDDEN:
            if re.search(pat, diff_text):
                bad.append(why)
        if bad:
            rec["status"] = "rejected"
            rec["reason"] = "沙盒检查未通过：含 %s" % "、".join(sorted(set(bad)))
            self.log.append(rec)
            return rec

        # ── 铁律 2：只写 .patch，不碰主文件 ──
        os.makedirs(self.pending_dir, exist_ok=True)
        safe = re.sub(r"[^\w.\-]", "_", name)[:60] or "patch"
        path = os.path.join(self.pending_dir, safe + ".patch")
        header = (
            "# 待人类授权的自我演化补丁\n"
            "# name  : %s\n"
            "# author: %s\n"
            "# ts    : %s\n"
            "# 目标  : %s\n"
            "# ---\n"
            "# 注意：本文件只是补丁，**未被应用**。应用需人类执行。\n\n"
            % (name, author, rec["ts"], ", ".join(norm))
        )
        with io.open(path, "w", encoding="utf-8", newline="\n") as f:
            f.write(header + diff_text)
        rec.update(status="pending_human_approval", patch_path=path,
                   reason="沙盒通过，已写 .patch 等待人类授权（未改任何主文件）")
        self.log.append(rec)
        return rec

    # ══════════ ② 判定 ─═════════
    def _is_protected(self, rel):
        r = rel.replace("\\", "/")
        for p in self.PROTECTED:
            if r == p or r.startswith(p.rstrip("/") + "/"):
                return True
        return False

    # ══════════ ③ 待办与授权（只标记，不替人应用）══════════
    def list_pending(self):
        if not os.path.isdir(self.pending_dir):
            return []
        return sorted(x for x in os.listdir(self.pending_dir) if x.endswith(".patch"))

    def approve(self, patch_name):
        """人类授权：**只做标记，不自动应用。**"""
        p = os.path.join(self.pending_dir, patch_name)
        if not os.path.isfile(p):
            return {"ok": False, "reason": "找不到 %s" % patch_name}
        marker = p + ".approved"
        with io.open(marker, "w", encoding="utf-8", newline="\n") as f:
            f.write("# 人类已授权（%s）。仍需人工执行应用。\n"
                    % time.strftime("%Y-%m-%dT%H:%M:%S"))
        return {"ok": True, "approved": True, "patch": patch_name,
                "reason": "已标记授权；本类不会自动应用补丁"}

    def summary(self):
        return {
            "proposals": len(self.log),
            "lethal_blocked": sum(1 for r in self.log if r.get("status") == "lethal"),
            "rejected": sum(1 for r in self.log if r.get("status") == "rejected"),
            "pending": len(self.list_pending()),
        }
