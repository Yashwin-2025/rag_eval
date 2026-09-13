"""
AETHER-OT: Lightweight Historian & Event Store (SQLite)
Stores real-time cyber telemetry, Modbus transactions, and incident dossiers (<50 MB RAM).
"""

import sqlite3
import json
import time
from typing import Dict, List, Optional, Any
from pathlib import Path


class HistorianDB:
    def __init__(self, db_path: str = "aether_ot_historian.db"):
        self.db_path = db_path
        self._init_db()

    def _get_conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        with self._get_conn() as conn:
            cursor = conn.cursor()
            # 1. Telemetry Time-Series
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS telemetry (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp REAL,
                    agv1_speed REAL,
                    agv1_batt REAL,
                    agv1_x REAL,
                    agv1_y REAL,
                    agv2_speed REAL,
                    agv2_batt REAL,
                    agv2_x REAL,
                    agv2_y REAL,
                    agv3_speed REAL,
                    agv3_batt REAL,
                    conv_speed REAL,
                    conv_running INTEGER,
                    s17_tripped INTEGER,
                    active_alarms INTEGER
                )
            """)
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_telemetry_time ON telemetry(timestamp)")

            # 2. Modbus Network Audit Log
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS network_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp REAL,
                    client_ip TEXT,
                    function_code INTEGER,
                    register_address INTEGER,
                    payload_value REAL,
                    is_authorized INTEGER,
                    note TEXT
                )
            """)
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_net_time ON network_events(timestamp)")

            # 3. Incident Dossiers
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS incidents (
                    incident_id TEXT PRIMARY KEY,
                    timestamp REAL,
                    severity TEXT,
                    root_cause TEXT,
                    mitre_ttp TEXT,
                    confidence REAL,
                    dossier_json TEXT
                )
            """)
            conn.commit()

    def log_telemetry(self, state: Dict):
        """Inserts a single state tick."""
        ts = time.time()
        agvs = state["agvs"]
        conv = state["conveyor"]
        s17 = state["sensors"]["SENSOR-17"]
        kpis = state["kpis"]

        with self._get_conn() as conn:
            conn.cursor().execute("""
                INSERT INTO telemetry (
                    timestamp, agv1_speed, agv1_batt, agv1_x, agv1_y,
                    agv2_speed, agv2_batt, agv2_x, agv2_y,
                    agv3_speed, agv3_batt, conv_speed, conv_running,
                    s17_tripped, active_alarms
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                ts,
                agvs["AGV-01"]["speed"], agvs["AGV-01"]["battery"], agvs["AGV-01"]["x"], agvs["AGV-01"]["y"],
                agvs["AGV-02"]["speed"], agvs["AGV-02"]["battery"], agvs["AGV-02"]["x"], agvs["AGV-02"]["y"],
                agvs["AGV-03"]["speed"], agvs["AGV-03"]["battery"],
                conv["speed_pct"], 1 if conv["is_running"] else 0,
                1 if s17["tripped"] else 0,
                kpis["active_alarm_count"],
            ))
            conn.commit()

    def log_network_event(self, client_ip: str, function_code: int, register: int, value: float, is_authorized: bool, note: str = ""):
        with self._get_conn() as conn:
            conn.cursor().execute("""
                INSERT INTO network_events (
                    timestamp, client_ip, function_code, register_address, payload_value, is_authorized, note
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (time.time(), client_ip, function_code, register, value, 1 if is_authorized else 0, note))
            conn.commit()

    def query_recent_telemetry(self, seconds: float = 60.0, limit: int = 50) -> List[Dict]:
        min_ts = time.time() - seconds
        with self._get_conn() as conn:
            rows = conn.cursor().execute("""
                SELECT * FROM telemetry WHERE timestamp >= ? ORDER BY timestamp DESC LIMIT ?
            """, (min_ts, limit)).fetchall()
            return [dict(r) for r in rows]

    def query_network_events(self, seconds: float = 120.0, limit: int = 50) -> List[Dict]:
        min_ts = time.time() - seconds
        with self._get_conn() as conn:
            rows = conn.cursor().execute("""
                SELECT * FROM network_events WHERE timestamp >= ? ORDER BY timestamp DESC LIMIT ?
            """, (min_ts, limit)).fetchall()
            return [dict(r) for r in rows]

    def save_incident(self, incident: Dict):
        with self._get_conn() as conn:
            conn.cursor().execute("""
                INSERT OR REPLACE INTO incidents (
                    incident_id, timestamp, severity, root_cause, mitre_ttp, confidence, dossier_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                incident["incident_id"],
                incident.get("timestamp", time.time()),
                incident.get("severity", "HIGH"),
                incident.get("root_cause", "Unknown"),
                json.dumps(incident.get("mitre_ics_mapping", [])),
                incident.get("confidence_score", 0.9),
                json.dumps(incident),
            ))
            conn.commit()

    def get_latest_incidents(self, limit: int = 10) -> List[Dict]:
        with self._get_conn() as conn:
            rows = conn.cursor().execute("""
                SELECT dossier_json FROM incidents ORDER BY timestamp DESC LIMIT ?
            """, (limit,)).fetchall()
            return [json.loads(r["dossier_json"]) for r in rows]
