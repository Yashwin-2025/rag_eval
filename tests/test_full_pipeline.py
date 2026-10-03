"""
End-to-End Pipeline Integration Test for AETHER-OT
"""
import pytest
from aether_ot.simulator.warehouse_sim import WarehouseSimulator
from aether_ot.plc.modbus_server import ModbusPLCBridge
from aether_ot.monitoring.historian import HistorianDB
from aether_ot.monitoring.tracer import get_trace_buffer, CyberPhysicalTracer
from aether_ot.analytics.anomaly_detector import ProcessAnomalyWatchdog
from aether_ot.agent.asset_graph import WarehouseAssetGraph
from aether_ot.agent.ai_detective import LangGraphAIDetective


def test_modbus_sync_and_tracer():
    sim = WarehouseSimulator()
    bridge = ModbusPLCBridge(simulator=sim)

    # Verify initial registers
    bridge.sync_from_simulator()
    assert bridge.hr_values[0] == 100  # AGV-01 speed 1.00 m/s
    assert bridge.hr_values[3] == 40   # Conveyor 40%

    # Trace recording
    CyberPhysicalTracer.record_modbus_span("10.0.0.99", 16, 40002, 220)
    traces = get_trace_buffer().get_recent_traces(limit=5)
    assert len(traces) > 0
    assert any(t["name"] == "span:modbus_packet_ingest" for t in traces)


def test_asset_graph_blast_radius():
    graph = WarehouseAssetGraph()
    blast = graph.get_blast_radius("PLC-01")
    assert "AGV-01" in blast["direct_dependents"]
    assert "AGV-02" in blast["direct_dependents"]


def test_rag_manual_search_maps_pgvector_rows(monkeypatch):
    from aether_ot.agent import sop_manuals

    monkeypatch.setattr(sop_manuals, "retrieve", lambda q, principal, k: [
        {"doc_id": "SOP-AGV-001", "content": "Zone B limit", "metadata": {"title": "AGV Limits"}, "distance": 0.2}
    ])
    hits = sop_manuals.RagManualRetriever().search_manuals("Zone B speed limit")
    assert hits == [{"doc_id": "SOP-AGV-001", "title": "AGV Limits", "content": "Zone B limit", "score": 0.8}]


def test_rag_manual_search_survives_db_outage(monkeypatch):
    from aether_ot.agent import sop_manuals

    def boom(*a, **k):
        raise RuntimeError("db down")

    monkeypatch.setattr(sop_manuals, "retrieve", boom)
    assert sop_manuals.RagManualRetriever().search_manuals("anything") == []


def test_langgraph_ai_detective_deterministic_investigation():
    historian = HistorianDB("test_pipeline_historian.db")
    historian.log_network_event("10.0.0.99", 16, 40002, 2.2, is_authorized=False)

    sim = WarehouseSimulator()
    sim.agvs["AGV-02"].speed = 2.2
    sim.agvs["AGV-02"].x = 14.0
    sim.agvs["AGV-02"].y = 6.0
    sim.tick(0.1)
    historian.log_telemetry(sim.get_state())

    detective = LangGraphAIDetective(historian=historian)
    dossier = detective.investigate({
        "code": "ALM-ZONEB-OVERSPEED",
        "message": "CRITICAL: AGV-02 triggered SENSOR-17 in Zone B. Conveyor interlocked."
    })

    assert dossier is not None
    assert dossier["severity"] == "CRITICAL"
    assert "10.0.0.99" in dossier["root_cause"]
    assert len(dossier["mitre_ics_mapping"]) > 0
    assert len(dossier["recommended_mitigation"]["actions"]) > 0
