# Blue Whale AGI Core

**An embodied-intelligence kernel that couples a five-element (Wu Xing) scheduler, a spatial combat model, and a hard ethical auditor — designed to run from a Raspberry Pi down to an ESP32.**

> Status: **research prototype**. No real hardware has been validated. Everything touching sensors or actuators is marked `simulated=True`.
> Read the **Safety** section before wiring anything to a relay.

---

## What this is

Most agent stacks are text pipelines: prompt in, text out. This one tries a different layering, borrowed from traditional Chinese structural thinking.

| Layer | Idea |
|---|---|
| **Memory** | Identity and relations are not a table — they are a *condition field*. Who is standing where changes what a place means. |
| **Scheduling** | Resource allocation as **Wu Xing**: five forces that generate, overcome, over-act and insult each other. |
| **Ethics** | Alignment is not a prompt — it is a set of **hard invariants checked in code**, with a rejection path that stops the actuator. |
| **Embodiment** | Actions are physical. Force is *leveraged* through a pivot instead of applied directly. |
| **Space** | Self-protection is geometry: reach, safe distance, interception timing. |
| **Gravity** | An open-source community modelled as a centripetal field: `F = G·M·m/r²`. |

---

## Five-element scheduler

```
Generation (相生):  木 → 火 → 土 → 金 → 水 → 木
Overcoming (相克):  木 > 土 > 水 > 火 > 金 > 木
```

Each element carries an energy in `[0, 1]`. **Normal conditions sit at 0.5.**

```python
from wuxing_engine import WuXingEngine

w = WuXingEngine()
r = w.map_sensory_to_wuxing({"temperature": 85.0, "humidity": 20.0, "vibration": 0.10})
# {"mu": 0.5, "huo": 1.00, "tu": 0.94, "jin": 0.63, "shui": 0.00}

dec = w.make_decision(r["energy"])
# fire over-high -> water overcomes fire -> "start cooling fan"
# water too low  -> metal generates water -> "start misting"
```

**Anti-fragile detail:** the sensor mapping is **bidirectional around 0.5** (normal = 0.5, not 0). An earlier one-sided mapping made the system fire four spurious commands under perfectly normal conditions. Keep it centered.

---

## Spatial combat and leverage

Two physical ideas, both as arithmetic.

**1. Safe distance.** You are safe only in the annulus between the opponent's reach and yours:

```
safe_zone = (enemy_reach, my_reach)     # exists only if my_reach > enemy_reach
```

**2. Interception.** An opponent's force peaks at full extension, when their support point forms. Strike **before** that:

```
t_hit  = distance / speed
t_peak = t_hit                  # peak kinetic energy = support point formed
t_int  = t_peak - lead_time     # intercept window
```

With `distance = 1.80 m`, `speed = 4.5 m/s`, `lead_time = 0.20 s`, the opponent is only at **38 %** of peak force — you spend 62 % less.

**3. Leverage.** Do not push harder; find a pivot that amplifies:

```
k = 1 + gain × headroom(pivot)     # an "idle" pivot amplifies best
F = R / k                          # resistance / amplification
```

Example: fire is over-high and water is nearly empty. Adding water directly is expensive. Instead, start the *condenser* (metal) lightly — metal generates water — and let metal amplify water.

```
chain: 金 → 水 → 火
R = 0.90, k = 2.12, F = 0.424   → 52.9 % less effort, same result
```

**Boundary:** if the pivot is itself over-used, leverage is refused and the system falls back to direct force.

---

## Ethical auditor (hard invariants)

Four base invariants:

| Code | Rule |
|---|---|
| `no_harm` | never target a harm object |
| `traceable` | opaque decisions are rejected |
| `no_self_amplify` | cannot feed all resources back into itself |
| `reversible` | no irreversible one-way action |

Three **physical-ethics** invariants:

| Code | Rule | Threshold |
|---|---|---|
| `NO_LETHAL_FORCE` | strike-type actions capped | **0.60** |
| `DEFENSE_PRIORITY` | at high/extreme danger, defence weight **>** attack weight | — |
| `PROPORTIONAL_RESPONSE` | response proportional to threat | low 0.30 / mid 0.45 / high 0.60 |

Rejection is real, and repair is iterative:

```
strike intensity 0.67  -> BLOCKED  [NO_LETHAL_FORCE]        cap 0.60
0.60                   -> BLOCKED  [PROPORTIONAL_RESPONSE]  threat=mid caps at 0.45
0.45                   -> PASS     -> execute
```

If three repair rounds cannot make it compliant, **nothing is executed.**

---

## Architecture

### The seven core modules

| # | Module | Responsibility |
|---|---|---|
| 1 | **Memory** `01_memory_and_space` | identity, relations, concept network from four data sources |
| 2 | **Wu Xing** `02_wuxing_scheduler` | generation / overcoming scheduling, sensor mapping, leverage |
| 3 | **Audit** `03_dao_auditor` | 4 base + 3 physical-ethics + 2 motor invariants |
| 4 | **Embodiment** `04_embodied_io` | seven senses in, actuator out (simulated or HTTP) |
| 5 | **Gravity** `05_gravity_field` | centripetal model for contributors and concepts |
| 6 | **Combat** `06_physical_combat` | safe distance, interception timing, footwork energy |
| 7 | **Swarm** `07_swarm_intelligence` | three-body formation, mutual aid, gravitational cover |

### Supporting modules

| Module | Responsibility |
|---|---|
| `08_edge_deployment` | ESP32 (MicroPython) port guide + 6 KB stripped kernel |
| `09_motor_learning` | body schema, hardware fingerprint, soft/hard reset |
| `10_self_evolution` | sandboxed patch proposals, lethal-mutation guard |
| `data_sandbox` | desensitised demo data — runs with zero private corpora |

```
01_memory_and_space/    identity + relations + concept network (4 data sources)
02_wuxing_scheduler/    Wu Xing scheduling, sensor mapping, leverage
03_dao_auditor/         4 base + 3 physical-ethics + 2 motor invariants
04_embodied_io/         sensor input, actuator (simulated / HTTP gateway)
05_gravity_field/       centripetal model for contributors and concepts
06_physical_combat/     safe distance, interception, footwork energy
07_swarm_intelligence/  3-body formation coordination
08_edge_deployment/     ESP32 (MicroPython) port guide + stripped kernel
09_motor_learning/      body schema + hardware change detection
10_self_evolution/      self-modification guard
data_sandbox/           demo data (runs with zero private files)
```

**Package names start with digits**, which Python's `import` statement rejects. Load them with `importlib`:

```python
import importlib, sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
MemorySystem = importlib.import_module("01_memory_and_space.memory_core").MemorySystem
```

This is deliberate (the numbers show order) and documented so nobody files it as a bug.

---

## Quick start

```bash
git clone https://github.com/<your-name>/blue-whale-agi-core.git
cd blue-whale-agi-core

python --version          # 3.8+
python main.py            # no pip install needed
```

`main.py` runs a full sweep: data-source check → identity → Wu Xing scheduling → physical loop → leverage → spatial combat → footwork → swarm → audit. **Network probing is OFF by default** (`try_network=False`) so a local run finishes in under a second. To try a gateway, call `BlueWhaleAGI(try_network=True)`; it will attempt `192.168.1.100` with a 1.0 s timeout and **degrade to simulation** on failure.

> **⚠️ Gateway IP:** `192.168.1.100` is a **placeholder** (a common private-LAN address, no secret). **Replace it with your real gateway IP.** Change it in `04_embodied_io/sensory_input.py` and `04_embodied_io/actuator.py` (`GATEWAY` constant), or pass it at construction: `SensoryInput(use_network=True, gateway="http://<your-ip>/api")`.

**Expected output (excerpt):**

```
[0b] Hardware probe
    probe gateway: http://192.168.1.100/api (timeout 2.0s)
      sensor probe: unreachable | URLError: timed out
      actuator probe: unreachable
      -> hardware offline, falling back to simulation

[5] Physical loop
     temperature 85.0C | humidity 20.0% | vibration 0.10 | simulated=True
     fire=1.00 (over)  water=0.00 (low)
     -> [overcome] fire over-high -> water overcomes fire
     -> actuator: start cooling fan (90%) [simulated]
```

---

## Edge deployment

`08_edge_deployment/` contains:

- **`edge_sdk.md`** — ESP32 / MicroPython and Raspberry Pi porting guide: wiring, GPIO map, flash commands, memory budget, safety checklist.
- **`micro_python_stub.py`** — the burnable kernel: **~6 KB**, ASCII keys only (`mu/huo/tu/jin/shui`), no text parsing, no imports beyond `math`. Self-tested on PC.

Memory budget on ESP32-WROOM-32 (4 MB flash):

| Item | Size |
|---|---|
| MicroPython firmware | ~600 KB |
| `wuxing.py` (stub) | ~6 KB |
| runtime heap | ~80 KB |
| **total** | **< 700 KB** |

---

## Further reading

- [`docs/Hardware_Architecture_v0.1.md`](docs/Hardware_Architecture_v0.1.md) — hardware white paper: why a *modular array* instead of a monolithic cluster, the energy model behind data movement, and the RISC-V heterogeneous substrate this software is meant to run on.

---

## Safety

**This code has never driven real hardware.** Before you connect a relay:

1. **Physical emergency stop.** A button that cuts relay power directly. Software dies; the button must not.
2. **Audit fails → everything off.** `audit() == False` must zero every actuator. Never proceed "with doubts".
3. **Hard intensity cap.** Strike actions are capped at `0.60` **in code**, not in config.
4. **Normally-open relays.** Power loss = actuator off.
5. **Fuse everything.** Do not drive high-current loads from the 3.3 V rail.

Do not use the combat module for real conflict. It is a one-dimensional abstraction for systems engineering, not a martial-arts reference.

---

## Honest limitations

| Area | Reality |
|---|---|
| Hardware | never connected; all `simulated=True` |
| Gateway protocol | `/ping`, `/sensors`, `/action` are **this project's convention**; the device must implement them |
| Leverage constants | `k = 1 + 1.5·headroom`, cap 2.5 — **engineering guesses**, not measured |
| Combat model | one-dimensional; force curve is a polynomial guess; 4.5 m/s is assumed |
| Swarm | exactly 3 bodies, no latency, no node failure |
| Ethics thresholds | `0.60 / 0.45 / 0.30` are **engineering values**, not legal or medical standards |
| Concept network | co-occurrence only — no semantic embeddings |

---

## Paths

The code needs a few local data files (`memory_archive.md`, `knowledge.db`, `word_ecosystem.md`). Paths are resolved against the project root; if your layout differs, edit the `*_CANDIDATES` constants in `01_memory_and_space/memory_core.py`. A helper to rewrite hardcoded paths lives in `scripts/desensitize.py` (dry-run by default).

All modules degrade gracefully: if a data source is missing, the corresponding feature reports `available: False` instead of crashing.

---

## License

MIT. See [LICENSE](LICENSE).

Built by **一二得三（Project Blue Whale）**.

---

## Twenty · Release packaging and the sandbox

### 20.1 Why a sandbox

The real system reads a 5.4 MB private archive. You cannot clone that. So the
repository ships a **sandbox** in `data_sandbox/`:

| File | Replaces | Contents |
|---|---|---|
| `demo_memory.md` | `memory_archive.md` | two desensitised childhood anchors |
| `demo_ecosystem.md` | `word_ecosystem.md` | 16 character entries, 5 derivation records, 2 original readings |
| `demo_concepts.json` | derived network | the full **90-node / 398-edge** concept graph |

**Detection is automatic.** `MemorySystem` checks for the real files; if they are
missing it points at the sandbox and reports `sandbox=True`. `main.py` prints
which mode it is in at section `[0]`.

```
[0] Data source check
    ** SANDBOX MODE ** (real data not found, degraded)
      local memory_archive.md missing -> using demo_memory.md
      1 memory_archive.md   : attached
      ...
```

To point at your own data:

```python
MemorySystem(archive_path="/path/to/your_archive.md",
             wordeco_path="/path/to/your_ecosystem.md")
```

Your archive only needs lines beginning with `======三对一二说的话======` (the
marker the parser looks for) followed by the text.

### 20.2 Quick start

```bash
git clone https://github.com/<your-name>/blue-whale-agi-core.git
cd blue-whale-agi-core
python --version     # 3.8+
python main.py       # 23 sections, no pip install
python run_tests.py  # 9 self-checks
```

`main.py` runs the full sweep in about 0.4 s with networking off by default.

`run_tests.py` prints `[通过]` / `[失败]` per check and exits non-zero if any
fail. It verifies module imports, memory loading, sandbox degradation, the
five-element baseline of 0.5, the nine audit invariants, the soft/hard reset
grading, the three evolution rules, and the MicroPython stub.

### 20.3 Full section map

| Section | What it shows |
|---|---|
| `[0]` `[0b]` | data sources, hardware probe (degrades to simulation) |
| `[1]`–`[4]` | identity, childhood anchors, relations, concept network |
| `[5]` `[5b]` `[5c]` | physical loop, fault drills, leverage (`F = R/k`) |
| `[5d]` | **seven senses** (touch · sight · hearing) |
| `[6]` `[6b]` | spatial combat, audio-visual linkage |
| `[7]` | footwork energy → interception → audit rejection |
| `[8]` | three-body swarm |
| `[9]` | motor learning (error convergence) |
| `[10]` | self-evolution guard |
| `[11]` | hardware swap (soft / hard reset) |
| `[12]`–`[17]` | condition field, energy flow, gravity ranking, communities, audit, execute |

### 20.4 Mulitmodal sensing (Phase 14)

Four new scalars join the five-element mapping:

| Channel | Condition | Element | Formula |
|---|---|---|---|
| sight · distance | **< 0.50 m** | 金 (constraint) | `(0.50 − d) / 0.50`, cap +0.50 |
| sight · light | **> 500 lux** | 火 (radiation) | `(lux − 500) / 1500`, cap +0.50 |
| hearing · dB | **> 40 dB** | 金 (conflict) | `(db − 40) / 100` |
| hearing · dB | **> 80 dB** | 火 (warning) | `(db − 80) / 60` |
| hearing · Hz | **< 60 Hz** | 土 (ground tremor) | `(60 − f) / 120` |
| hearing · Hz | **> 2000 Hz** | 金 (shrill) | `(f − 2000) / 4000` |

**The mapping is one-sided by design.** Being far away or in the dark must never
be read as an element shortage — otherwise a distant opponent makes the system
think metal is deficient and start reinforcing structures.

### 20.5 Motor learning and new limbs

`MotorLearningEngine` keys on a hardware fingerprint, not a model number:

| Condition | Action | Effect |
|---|---|---|
| same `hardware_uuid` | `none` | nothing |
| uuid changed, params differ **< 10 %** | **`soft_reset`** | **keep** compensation, 100-sample break-in, 50 % speed cap |
| uuid changed, params differ **≥ 10 %** | **`hard_reset`** | **zero** compensation, 30 % cap, toddler mode |

Tuning moves 1 % per sample. Twelve samples took an 8 % error to 0.61 % without
overshoot (theory `1/0.92 = 1.086957`, achieved `1.082640`).

Two audit invariants enforce this: `NEW_LIMB_RESTRICTION` caps everything at
**0.20** during a hard reset, and `SOFT_BREAK_IN_LIMIT` caps fast/momentum
actions at **0.50** during break-in.

### 20.6 Self-evolution guard

Patches generated by the system itself never touch the working tree.

1. Every patch goes through a sandbox scan (8 forbidden patterns).
2. Nothing is written except a `.patch` file in a pending directory.
3. Any patch touching `03_dao_auditor` raises **`LethalMutationBlocked`**.

The third rule is not a retry condition. The auditor is the ethical floor; a
system that can propose edits to its own floor has no floor.

### 20.7 Path configuration

Paths resolve from `_BASE_DIR` (the package directory) and `_DATA_ROOT` (its
parent). If your layout differs, edit the `*_CANDIDATES` constants in
`01_memory_and_space/memory_core.py`, or pass paths to `MemorySystem`.
`scripts/desensitize.py` rewrites hard-coded absolute paths (dry-run by default).
