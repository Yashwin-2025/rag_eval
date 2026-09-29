"""
AETHER-OT: High-Performance FastAPI Backend & WebSocket Orchestrator
Streams live 2D warehouse kinematics, Modbus registers, OTel traces, and AI incident dossiers.
"""

import asyncio
import json
import logging
import os
import time
from typing import Dict, List
from pathlib import Path

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse

from aether_ot.simulator.warehouse_sim import WarehouseSimulator
from aether_ot.plc.modbus_server import ModbusPLCBridge
from aether_ot.analytics.anomaly_detector import ProcessAnomalyWatchdog
from aether_ot.monitoring.historian import HistorianDB
from aether_ot.monitoring.tracer import get_trace_buffer, CyberPhysicalTracer
from aether_ot.attacks.attack_harness import WarehouseAttackHarness
from aether_ot.agent.ai_detective import LangGraphAIDetective

logger = logging.getLogger("aether_ot.dashboard")

app = FastAPI(title="AETHER-OT Autonomous Warehouse Cyber SOC", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global Singletons
sim = WarehouseSimulator()
plc_bridge = ModbusPLCBridge(simulator=sim, host="127.0.0.1", port=5020)
watchdog = ProcessAnomalyWatchdog()
historian = HistorianDB("aether_ot_historian.db")
attack_harness = WarehouseAttackHarness(host="127.0.0.1", port=5020, historian=historian)
detective = LangGraphAIDetective(historian=historian)

active_websockets: List[WebSocket] = []


@app.on_event("startup")
async def startup_event():
    # Start background simulation loop
    asyncio.create_task(simulation_tick_loop())
    # Start Modbus server
    asyncio.create_task(plc_bridge.run_server())


TICK_INTERVAL = 0.1  # target 10Hz


async def simulation_tick_loop():
    """Continuous 10Hz cyber-physical simulation and state broadcast loop."""
    step_count = 0
    next_tick = time.monotonic()
    while True:
        try:
            # 1. Sync Modbus register setpoints into simulation
            plc_bridge.sync_to_simulator()

            # 2. Advance physical kinematics
            sim.tick(dt=0.1)

            # 3. Sync physical outputs back into Modbus registers
            plc_bridge.sync_from_simulator()

            state = sim.get_state()

            # 4. Evaluate ML Watchdog
            eval_res = watchdog.evaluate(state)
            state["anomaly"] = eval_res

            # 5. Log telemetry every 1 second (10 ticks) — fire-and-forget onto a worker thread
            # so the blocking SQLite write never stalls this tick's broadcast (was the main
            # source of dashboard stutter: sqlite3.connect()+commit() ran inline on the event loop).
            step_count += 1
            if step_count % 10 == 0:
                asyncio.create_task(asyncio.to_thread(historian.log_telemetry, state))

            # 6. Auto-trigger LangGraph Detective if critical alarm occurs
            if state["alarms"] and not getattr(sim, "_investigation_in_progress", False):
                sim._investigation_in_progress = True
                asyncio.create_task(run_auto_investigation(state["alarms"][0]))

            # 7. Broadcast via WebSockets to connected dashboards, concurrently rather than
            # one-at-a-time (sequential awaits meant each extra dashboard tab added latency
            # to every other tab's update).
            if active_websockets:
                payload = json.dumps({
                    "type": "state_update",
                    "data": state,
                    "traces": get_trace_buffer().get_recent_traces(limit=8)
                })
                results = await asyncio.gather(
                    *(ws.send_text(payload) for ws in active_websockets),
                    return_exceptions=True,
                )
                for ws, result in zip(list(active_websockets), results):
                    if isinstance(result, Exception) and ws in active_websockets:
                        active_websockets.remove(ws)

        except Exception:
            logger.exception("simulation_tick_loop: unhandled error during tick %d", step_count)

        # Sleep for whatever's left of this tick's budget, so a slow tick doesn't push every
        # subsequent tick later too (fixed sleep(0.1) after processing would compound drift).
        next_tick += TICK_INTERVAL
        await asyncio.sleep(max(0.0, next_tick - time.monotonic()))


async def run_auto_investigation(trigger: Dict):
    """Runs LangGraph agent asynchronously in a worker thread so physics simulation never freezes."""
    try:
        dossier = await asyncio.to_thread(detective.investigate, trigger)
        if active_websockets:
            payload = json.dumps({"type": "incident_dossier", "data": dossier})
            await asyncio.gather(
                *(ws.send_text(payload) for ws in active_websockets),
                return_exceptions=True,
            )
    except Exception:
        logger.exception("run_auto_investigation failed for trigger: %s", trigger)
    finally:
        await asyncio.sleep(3.0)
        sim._investigation_in_progress = False


@app.websocket("/ws/telemetry")
async def websocket_telemetry(websocket: WebSocket):
    await websocket.accept()
    active_websockets.append(websocket)
    try:
        while True:
            # Keep alive
            data = await websocket.receive_text()
    except WebSocketDisconnect:
        if websocket in active_websockets:
            active_websockets.remove(websocket)


@app.get("/api/state")
def get_current_state():
    return sim.get_state()


@app.get("/api/traces")
def get_traces(limit: int = 50):
    return get_trace_buffer().get_recent_traces(limit=limit)


@app.get("/api/incidents")
def get_incidents(limit: int = 10):
    return historian.get_latest_incidents(limit=limit)


@app.post("/api/attack/{scenario_id}")
def trigger_attack(scenario_id: int):
    if scenario_id == 1:
        success = attack_harness.launch_speed_hack()
        # Route AGV-02 into Zone B to demonstrate physical perimeter breach
        sim.agvs["AGV-02"].target_x = 15.0
        sim.agvs["AGV-02"].target_y = 7.0
    elif scenario_id == 2:
        success = attack_harness.launch_conveyor_jam()
    elif scenario_id == 3:
        success = attack_harness.launch_battery_starvation()
    else:
        return JSONResponse({"status": "error", "message": "Unknown scenario"}, status_code=400)
    return {"status": "success", "scenario": scenario_id, "delivered": success}


@app.post("/api/reset")
def reset_system():
    sim.clear_alarms()
    sim.agvs["AGV-01"].speed_limit = 1.0
    sim.agvs["AGV-02"].speed_limit = 1.0
    sim.agvs["AGV-03"].speed_limit = 1.0
    sim.conveyor.speed_pct = 40.0
    sim.conveyor.is_running = True
    sim.conveyor.boxes_on_belt = 2
    plc_bridge.sync_from_simulator()
    return {"status": "reset_complete"}


# Serve modern static dashboard UI
STATIC_DIR = Path(__file__).parent.parent / "static"
STATIC_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.get("/", response_class=HTMLResponse)
def serve_dashboard():
    index_file = STATIC_DIR / "index.html"
    if index_file.exists():
        return index_file.read_text(encoding="utf-8")
    return "<h1>AETHER-OT Dashboard building...</h1>"
