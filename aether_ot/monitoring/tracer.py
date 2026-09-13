"""
AETHER-OT: OpenTelemetry (OTel) Distributed Tracing Engine
Instruments cyber-physical telemetry, Modbus transactions, and LangGraph agent execution.
"""

from typing import Dict, List, Optional, Any
import time
import uuid
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor, SpanExporter, SpanExportResult
from opentelemetry.trace import Status, StatusCode


class LocalTraceBufferExporter(SpanExporter):
    """
    In-memory OpenTelemetry span exporter.
    Maintains a rolling ring buffer of recent spans for live UI visualization and evaluation audits.
    Zero external collector required (consumes < 10 MB RAM).
    """

    def __init__(self, max_spans: int = 1000):
        self.max_spans = max_spans
        self.spans: List[Dict[str, Any]] = []

    def export(self, spans) -> SpanExportResult:
        for span in spans:
            start_time_sec = span.start_time / 1e9 if span.start_time else time.time()
            end_time_sec = span.end_time / 1e9 if span.end_time else time.time()
            duration_ms = round((end_time_sec - start_time_sec) * 1000, 2)

            span_record = {
                "trace_id": format(span.context.trace_id, "032x"),
                "span_id": format(span.context.span_id, "016x"),
                "parent_id": format(span.parent.span_id, "016x") if span.parent else None,
                "name": span.name,
                "start_time": start_time_sec,
                "end_time": end_time_sec,
                "duration_ms": duration_ms,
                "status": span.status.status_code.name if span.status else "UNSET",
                "attributes": dict(span.attributes) if span.attributes else {},
            }
            self.spans.append(span_record)
            if len(self.spans) > self.max_spans:
                self.spans.pop(0)
        return SpanExportResult.SUCCESS

    def shutdown(self):
        self.spans.clear()

    def get_recent_traces(self, limit: int = 50) -> List[Dict[str, Any]]:
        return self.spans[-limit:]

    def get_spans_by_trace_id(self, trace_id: str) -> List[Dict[str, Any]]:
        return [s for s in self.spans if s["trace_id"] == trace_id]


# Singleton global tracer configuration
_exporter = LocalTraceBufferExporter()
_provider = TracerProvider()
_provider.add_span_processor(SimpleSpanProcessor(_exporter))
trace.set_tracer_provider(_provider)
otel_tracer = trace.get_tracer("aether_ot.cyber_physical", "1.0.0")


def get_trace_buffer() -> LocalTraceBufferExporter:
    return _exporter


class CyberPhysicalTracer:
    """Convenience helper for instrumenting cyber-physical workflows."""

    @staticmethod
    def start_incident_trace(incident_id: str, trigger_source: str):
        """Creates a root trace for an operational incident or cyberattack."""
        span = otel_tracer.start_span("incident_lifecycle")
        span.set_attribute("incident.id", incident_id)
        span.set_attribute("incident.trigger", trigger_source)
        span.set_attribute("otel.library.name", "aether_ot")
        return span

    @staticmethod
    def record_modbus_span(client_ip: str, function_code: int, register: int, value: Any):
        with otel_tracer.start_as_current_span("span:modbus_packet_ingest") as span:
            span.set_attribute("net.peer.ip", client_ip)
            span.set_attribute("modbus.function_code", function_code)
            span.set_attribute("modbus.register", register)
            span.set_attribute("modbus.payload_value", str(value))
            if client_ip != "127.0.0.1" and client_ip != "10.0.0.10":
                span.set_status(Status(StatusCode.ERROR, f"Unauthorized client {client_ip}"))
            else:
                span.set_status(Status(StatusCode.OK))

    @staticmethod
    def record_plc_execution(register: int, old_val: float, new_val: float, asset_id: str):
        with otel_tracer.start_as_current_span("span:plc_state_transition") as span:
            span.set_attribute("plc.asset_id", asset_id)
            span.set_attribute("plc.register", register)
            span.set_attribute("plc.old_value", old_val)
            span.set_attribute("plc.new_value", new_val)

    @staticmethod
    def record_physical_anomaly(asset_id: str, metric: str, value: float, threshold: float):
        with otel_tracer.start_as_current_span("span:physical_simulation_tick") as span:
            span.set_attribute("physical.asset_id", asset_id)
            span.set_attribute("physical.metric", metric)
            span.set_attribute("physical.value", value)
            span.set_attribute("physical.threshold", threshold)
            if value > threshold:
                span.set_status(Status(StatusCode.ERROR, f"{metric} exceeded threshold {threshold}"))

    @staticmethod
    def record_agent_span(node_name: str, inputs: Dict, outputs: Dict, duration_ms: float):
        with otel_tracer.start_as_current_span(f"span:langgraph_{node_name}") as span:
            span.set_attribute("agent.node", node_name)
            span.set_attribute("agent.duration_ms", duration_ms)
            for k, v in inputs.items():
                span.set_attribute(f"agent.input.{k}", str(v)[:100])
            span.set_status(Status(StatusCode.OK))
