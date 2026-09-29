# PROJECT.md — AETHER-OT

**AETHER-OT** (Autonomous Engineering & Threat Hypothesizing Engine for Real-Time Operational
Technology) is a from-scratch **digital twin of an industrial warehouse**, built to demonstrate
detecting and investigating cyberattacks against OT (operational technology) systems — the
control-systems world of PLCs, SCADA, Modbus, AGVs — using AI. It's grounded in real standards
(IEC 62443, NIST SP 800-82, MITRE ATT&CK for ICS), documented in
`docs/industrial_ai_ot_cybersecurity_blueprint.md`.

Lives in `aether_ot/`, launched by `run_system.py`.

---

## Architecture

```
simulator/warehouse_sim.py    2D physics sim: 3 AGVs, 1 conveyor, safety zones, batteries
        ↓ state
plc/modbus_server.py          Real Modbus TCP server — exposes sim state as PLC registers
        ↓ polled by
analytics/anomaly_detector.py Isolation Forest (scikit-learn) watching telemetry for drift
monitoring/historian.py       SQLite time-series log of telemetry + network events + incidents
monitoring/tracer.py          OpenTelemetry spans for Modbus reads/writes (audit trail)
        ↓ on alert
agent/ai_detective.py         LangGraph multi-agent investigator (triage → network forensics →
                               process forensics → asset blast-radius → SOP retrieval → safety
                               verification → incident dossier), backed by an LLM via OpenRouter
agent/asset_graph.py          Graph model of warehouse assets for blast-radius reasoning
agent/qdrant_indexer.py       Vector index (Qdrant, embedded) of operating manuals/SOPs for RAG
attacks/attack_harness.py     Attack scripts: e.g. write malicious speed setpoints over Modbus
                               (MITRE T0855/T0836), simulating a real ICS intrusion
eval/eval_harness.py          Scores the detective's incident dossiers against ground truth
dashboard/backend/main.py     FastAPI + WebSocket server: pushes live sim state to a 3D dashboard
dashboard/static/index.html   3D visualization of the warehouse + live alerts
```

`run_system.py` boots the whole thing: Qdrant index → FastAPI/WebSocket dashboard on
`:8000` → Modbus PLC bridge on `127.0.0.1:5020`.

**The narrative it demonstrates:** an attacker writes a bad setpoint to a PLC register over
Modbus → the physics sim reacts (AGV overspeeds, trips a safety sensor) → the anomaly detector
flags the deviation → an LLM-driven LangGraph agent investigates network + process evidence,
reasons over the asset graph to find blast radius, retrieves the relevant SOP, verifies its
proposed mitigation is *safe* before suggesting it, and produces an incident report — all visible
live on a 3D dashboard.

**Run it:**
```bash
pip install -r requirements.txt
python run_system.py
# dashboard: http://localhost:8000
# in another shell, launch an attack:
python -m aether_ot.attacks.attack_harness
```

---

## How to learn from this codebase

Read in this order — each step is a self-contained concept you can verify by running it:

1. **`aether_ot/simulator/warehouse_sim.py`** — pure Python state machine, no dependencies on the
   rest of the system. Understand the physical model first (positions, speeds, battery drain,
   safety zones) since everything downstream reacts to this state.
2. **`aether_ot/plc/modbus_server.py`** — see how simulator state gets exposed as Modbus holding
   registers. `pymodbus` is a real library, not a mock — this is the actual protocol real
   ICS attackers/defenders use.
3. **`aether_ot/attacks/attack_harness.py`** — run an attack (`launch_speed_hack`) and watch it
   write a register over the network like a real intrusion would. This is the cheapest way to see
   cause → effect.
4. **`aether_ot/analytics/anomaly_detector.py`** — a compact, readable example of using
   `IsolationForest` for unsupervised anomaly detection on a small multivariate feature vector.
5. **`aether_ot/monitoring/historian.py` + `tracer.py`** — the audit trail. Notice how every
   Modbus write and telemetry sample is logged *before* any AI reasoning happens.
6. **`aether_ot/agent/ai_detective.py`** — the centerpiece. Read the `StateGraph` node-by-node:
   `triage → investigate_network → investigate_process → reason_topology → retrieve_sop →
   verify_mitigation_safety → synthesize_dossier`. Good example of LangGraph conditional routing
   (`_route_investigation`) and separating evidence-gathering from reasoning from a final
   safety check before acting.
7. **`aether_ot/dashboard/backend/main.py`** — how the FastAPI `/ws/telemetry` WebSocket streams
   simulator state at loop cadence to the frontend.
8. **`docs/industrial_ai_ot_cybersecurity_blueprint.md`** — the domain knowledge (Purdue model,
   IT/OT segmentation, protocol behavior) that the simulator/attacks are modeling.

**What's genuinely reusable beyond OT specifics:**
- The LangGraph "evidence-gathering → reasoning → safety-gated action" pattern generalizes to any
  agent that should investigate before acting (incident response, support triage, etc.).
- The Isolation Forest + hand-bootstrapped baseline pattern generalizes to any "detect anomalies
  in a small telemetry vector with no labeled anomaly data" problem.
- The historian-before-reasoning pattern (log raw facts immediately, let the AI reason over logs
  afterward) is a solid general principle for any auditable AI system.

---

## Optimizing the running application

The core loop is `simulation_tick_loop()` in `aether_ot/dashboard/backend/main.py:55` — it runs
at a target 10Hz (`asyncio.sleep(0.1)`), and every stage in it runs on the single asyncio event
loop. That means anything blocking in that loop directly steals time from physics ticks *and*
WebSocket broadcast latency. In order of impact:

1. **`historian.log_telemetry()` is a blocking synchronous SQLite call made directly inside the
   async tick loop** (`main.py:78`, `historian.py:86`). Every call does
   `sqlite3.connect()` → insert → `commit()` — opening a fresh connection and forcing an fsync
   *inside* the event loop, once per second. Under any disk contention this stalls the whole
   sim/dashboard for that tick. Fixes, cheapest first:
   - `PRAGMA journal_mode=WAL` + `PRAGMA synchronous=NORMAL` on the connection — biggest win for
     least effort, avoids fsync-per-commit.
   - Keep one persistent connection (module-level, not reopened per call) instead of
     `sqlite3.connect()` on every insert/query.
   - Move the actual write off the event loop with `asyncio.to_thread(historian.log_telemetry, state)`,
     the same pattern already used for `run_auto_investigation` (`main.py:110`).

2. **WebSocket broadcast is sequential, not concurrent** (`main.py:92-99`): `await ws.send_text()`
   in a `for` loop means N clients are served one after another, each one adding latency before
   the next. Swap to:
   ```python
   results = await asyncio.gather(
       *(ws.send_text(payload) for ws in active_websockets), return_exceptions=True
   )
   ```
   and drop sockets whose result is an exception. Matters once you have more than a couple of
   dashboard tabs open.

3. **Fixed-delay tick pacing drifts under load** (`main.py:104`, `await asyncio.sleep(0.1)`):
   this sleeps 0.1s *after* processing finishes, so actual tick rate is `1 / (0.1 + processing_time)`,
   not a true 10Hz. Track a monotonic `next_tick` timestamp and sleep
   `max(0, next_tick - time.monotonic())` instead, so slow ticks don't compound into drift.

4. **Bare `except Exception: pass` swallows every error in the tick loop** (`main.py:101-102`).
   This hides the exact stalls/bugs you'd be optimizing for. At minimum log it
   (`logger.exception(...)`) — silent failure makes performance regressions invisible.

5. **`json.dumps` of the full warehouse state every 100ms** (`main.py:87-91`) — currently cheap
   at this entity count (3 AGVs, 1 conveyor), but won't scale if you add more assets. If you
   extend the simulator, consider `orjson` (C-accelerated) or sending only changed fields
   (delta encoding) instead of the full state each tick.

6. **`CORSMiddleware` with `allow_origins=["*"]` and `allow_credentials=True`** (`main.py:28-34`)
   is a spec-invalid combination — most browsers will actually reject the credentialed request
   this implies. Not a runtime performance issue, but worth fixing if you ever see CORS errors
   that don't match what the code "should" allow: either drop `allow_credentials`, or pin
   `allow_origins` to your actual dashboard origin.

None of these matter yet at 3 AGVs / 1 dashboard tab — the app is I/O-light. They matter the
moment you (a) add more simulated assets, (b) open multiple dashboard clients, or (c) run under
disk contention (e.g. containerized with a network volume) — the SQLite write in particular is the
one most likely to cause visible tick stutter first.
