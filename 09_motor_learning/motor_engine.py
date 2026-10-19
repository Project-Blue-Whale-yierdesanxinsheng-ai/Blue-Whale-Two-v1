# -*- coding: utf-8 -*-
"""09 · 运动反馈学习（MotorLearningEngine）。

三要解决的真实问题：
    **同一型号的电机换一只，误差补偿也会失效。**
    因为每只电机有自己的公差、间隙、延迟。

所以身体记忆不能只记「型号」，必须记 **硬件指纹 `hardware_uuid`**。
换件时按参数差异分三级处理：

    同一 uuid                        → 不做任何事
    不同 uuid，参数差异 < 10%         → **软重置** soft_reset
                                       保留旧系数，进入磨合期（100 次），每次只调 1%
    不同 uuid，参数差异 ≥ 10%         → **硬重置** hard_reset
                                       旧补偿清零，限速 30%，进入"幼儿学步"

**关键：软重置不清零。** 同型号换件，旧的肌肉记忆还有用 —— 只是要重新校准。
"""


class MotorLearningEngine:
    """运动学习：身体图式 + 误差补偿 + 换件检测。"""

    SOFT_DIFF_THRESHOLD = 0.10     # 参数差异阈值（10%）
    GRACE_SAMPLES = 100            # 磨合期样本数
    TUNE_STEP = 0.01               # 每次只调 1%
    HARD_LIMIT = 0.30              # 硬重置后的限速（30%）

    def __init__(self, body_schema=None):
        self.body_schema = body_schema or {
            "hardware_uuid": "MOTOR-A-0001",
            "length_m": 0.30,
            "torque_nm": 1.20,
            "latency_ms": 8.0,
        }
        # 补偿系数（"肌肉记忆"）
        self.scale = 1.00          # 距离缩放
        self.offset = 0.00         # 零点偏移（米）
        self.mode = "normal"       # normal / soft_reset / hard_reset
        self.grace_left = 0        # 剩余磨合次数
        self.limit = 1.0           # 动作强度上限系数
        self.samples = 0
        self.last_error = 0.0
        self.history = []

    # ══════════ ① 换件检测 ══════════
    def _param_diff(self, a, b):
        """算三个物理参数的最大相对差异。"""
        keys = ("length_m", "torque_nm", "latency_ms")
        worst, which = 0.0, ""
        for k in keys:
            if k not in a or k not in b:
                continue
            old = float(a[k])
            new = float(b[k])
            base = abs(old) if abs(old) > 1e-9 else 1.0
            d = abs(new - old) / base
            if d > worst:
                worst, which = d, k
        return worst, which

    def detect_hardware_change(self, new_schema):
        """换件检测：返回 {action, diff, ...}。"""
        old = self.body_schema
        new = dict(new_schema)

        old_uid = old.get("hardware_uuid")
        new_uid = new.get("hardware_uuid")
        diff, worst_key = self._param_diff(old, new)

        out = {
            "old_uuid": old_uid,
            "new_uuid": new_uid,
            "uuid_changed": old_uid != new_uid,
            "param_diff": round(diff, 4),
            "worst_param": worst_key,
        }

        if not out["uuid_changed"]:
            out.update(action="none", reason="uuid 未变 → 同一只硬件，无需重校准",
                       limit=self.limit, grace_left=self.grace_left)
            self.history.append(("detect", out))
            return out

        if diff < self.SOFT_DIFF_THRESHOLD:
            # ── 软重置：同型号替换 ──
            self.body_schema = new
            self.mode = "soft_reset"
            self.grace_left = self.GRACE_SAMPLES
            self.limit = 0.50            # 磨合期限速 50%
            # **不清零**：scale / offset 保留
            out.update(
                action="soft_reset",
                reason=("uuid 变了但参数差异 %.1f%% < 10%% → 同型号替换，"
                        "**保留旧补偿**，进入 %d 次磨合，限速 50%%"
                        % (diff * 100, self.GRACE_SAMPLES)),
                keep_scale=round(self.scale, 4),
                keep_offset=round(self.offset, 4),
                limit=self.limit,
                grace_left=self.grace_left,
            )
        else:
            # ── 硬重置：换新形态 ──
            self.body_schema = new
            self.mode = "hard_reset"
            self.grace_left = self.GRACE_SAMPLES
            self.limit = self.HARD_LIMIT   # 限速 30%
            old_scale, old_offset = self.scale, self.offset
            self.scale = 1.00              # 清零
            self.offset = 0.00             # 清零
            out.update(
                action="hard_reset",
                reason=("uuid 变了且参数差异 %.1f%%（%s）≥ 10%% → 换新形态，"
                        "**旧补偿清零**，限速 30%%，幼儿学步"
                        % (diff * 100, worst_key)),
                cleared_scale=(round(old_scale, 4), 1.0),
                cleared_offset=(round(old_offset, 4), 0.0),
                limit=self.limit,
                grace_left=self.grace_left,
            )

        self.history.append(("detect", out))
        return out

    # ══════════ ② 增量微调 ══════════
    def incremental_tuning(self, actual_distance, commanded_distance):
        """按实测误差微调补偿。**每次只动 1%。**

        actual 比 commanded 短 → 说明电机出力不足 → scale 往上补
        """
        cmd = float(commanded_distance)
        act = float(actual_distance)
        if cmd <= 1e-9:
            return {"skipped": True, "reason": "commanded_distance 为 0"}

        err = act - cmd                     # 正 = 走多了，负 = 走少了
        err_ratio = err / cmd
        self.last_error = err_ratio
        self.samples += 1

        before = self.scale
        # 每次只调 1%（乘以误差方向）
        step = self.TUNE_STEP
        if err_ratio < 0:
            self.scale = min(2.0, self.scale * (1.0 + step))
        elif err_ratio > 0:
            self.scale = max(0.5, self.scale * (1.0 - step))

        if self.grace_left > 0:
            self.grace_left -= 1

        # 磨合完成判定：次数用完 AND 误差 < 2%
        recovered = False
        if self.grace_left == 0 and abs(err_ratio) < 0.02 and self.mode != "normal":
            self.mode = "normal"
            self.limit = 1.0
            recovered = True
        elif self.grace_left == 0 and self.mode == "hard_reset" and abs(err_ratio) < 0.02:
            self.mode = "normal"
            self.limit = 1.0
            recovered = True

        out = {
            "samples": self.samples,
            "commanded": cmd,
            "actual": act,
            "error_m": round(err, 5),
            "error_pct": round(err_ratio * 100, 2),
            "scale_before": round(before, 6),
            "scale_after": round(self.scale, 6),
            "grace_left": self.grace_left,
            "mode": self.mode,
            "limit": self.limit,
            "recovered": recovered,
        }
        self.history.append(("tune", out))
        return out

    # ══════════ ③ 应用补偿 ══════════
    def apply_compensation(self, commanded_distance):
        """把补偿作用到指令上，并按当前限速封顶。"""
        out = commanded_distance * self.scale + self.offset
        return {
            "commanded": round(float(commanded_distance), 5),
            "compensated": round(out, 5),
            "scale": round(self.scale, 6),
            "offset": round(self.offset, 6),
            "mode": self.mode,
            "limit": self.limit,
        }

    # ══════════ ④ 状态 ══════════
    def status(self):
        return {
            "uuid": self.body_schema.get("hardware_uuid"),
            "schema": dict(self.body_schema),
            "mode": self.mode,
            "scale": round(self.scale, 6),
            "offset": round(self.offset, 6),
            "limit": self.limit,
            "grace_left": self.grace_left,
            "samples": self.samples,
            "last_error_pct": round(self.last_error * 100, 2),
        }
