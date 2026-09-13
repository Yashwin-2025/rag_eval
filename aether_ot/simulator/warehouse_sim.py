"""
AETHER-OT: 2D Autonomous Warehouse Physics & Cyber-Physical Simulator
Simulates continuous kinematics, battery kinetics, conveyor transfer, and safety zones.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
import math
import time
import random


@dataclass
class AGV:
    id: str
    name: str
    x: float
    y: float
    target_x: float
    target_y: float
    speed: float = 1.0  # Current speed m/s
    speed_limit: float = 1.2  # Max allowed speed m/s (PLC setpoint)
    battery: float = 100.0  # 0 to 100%
    is_charging: bool = False
    charging_dock_id: Optional[str] = None
    state: str = "IDLE"  # IDLE, MOVING, PICKING, CHARGING, STOPPED, FAULT
    has_package: bool = False
    current_order_id: Optional[str] = None
    in_restricted_zone: bool = False
    safety_halt: bool = False
    color: str = "#10B981"  # Emerald green, turns red upon hack/fault


@dataclass
class Conveyor:
    id: str
    name: str
    speed_pct: float = 40.0  # 0 to 100%
    is_running: bool = True
    boxes_on_belt: int = 2
    max_capacity: int = 10
    jammed: bool = False
    throughput_items_per_min: float = 12.0


@dataclass
class SafetySensor:
    id: str
    name: str
    zone: str
    tripped: bool = False
    trip_reason: str = ""


class WarehouseSimulator:
    """
    Continuous 2D Warehouse Digital Twin.
    Grid Size: 20m x 20m.
    Contains 3 AGVs, 1 Conveyor, 2 Pick Stations, 1 Pack Station, 2 Chargers, 1 Restricted Zone.
    """

    def __init__(self):
        # Grid boundaries
        self.width = 20.0
        self.height = 20.0

        # AGVs
        self.agvs: Dict[str, AGV] = {
            "AGV-01": AGV(id="AGV-01", name="Forklift-01", x=4.0, y=4.0, target_x=4.0, target_y=14.0),
            "AGV-02": AGV(id="AGV-02", name="Tugger-02", x=8.0, y=4.0, target_x=10.0, target_y=14.0),
            "AGV-03": AGV(id="AGV-03", name="Lifter-03", x=12.0, y=4.0, target_x=2.0, target_y=2.0),
        }

        # Conveyor
        self.conveyor = Conveyor(id="CONV-01", name="Main Intake Conveyor")

        # Stations
        self.pick_station_1 = (4.0, 14.0)
        self.pick_station_2 = (10.0, 14.0)
        self.pack_station = (16.0, 18.0)
        self.charge_dock_1 = (2.0, 2.0)
        self.charge_dock_2 = (6.0, 2.0)

        # Restricted Zone B (Hazardous Mechanical Lifter Zone)
        # X: 12.0 to 18.0, Y: 4.0 to 10.0
        self.zone_b = {"min_x": 12.0, "max_x": 18.0, "min_y": 4.0, "max_y": 10.0}

        # Safety Sensors & Interlocks
        self.safety_sensors: Dict[str, SafetySensor] = {
            "SENSOR-17": SafetySensor(id="SENSOR-17", name="Zone-B Pedestrian Laser Guard", zone="Zone B"),
            "SENSOR-21": SafetySensor(id="SENSOR-21", name="Conveyor Jam Optical Sensor", zone="Conveyor"),
            "SENSOR-01": SafetySensor(id="SENSOR-01", name="Emergency Plant E-Stop", zone="Master"),
        }

        # Metrics
        self.completed_orders: int = 0
        self.order_throughput_hourly: float = 142.0
        self.active_alarms: List[Dict] = []
        self.sim_time: float = 0.0
        self.is_paused: bool = False

    def is_in_zone_b(self, x: float, y: float) -> bool:
        return (
            self.zone_b["min_x"] <= x <= self.zone_b["max_x"]
            and self.zone_b["min_y"] <= y <= self.zone_b["max_y"]
        )

    def tick(self, dt: float = 0.1):
        """
        Step simulation forward by dt seconds (typically called 10 times a second).
        """
        if self.is_paused:
            return

        self.sim_time += dt

        # 1. Update AGVs
        for agv_id, agv in self.agvs.items():
            if agv.safety_halt:
                agv.state = "STOPPED"
                agv.color = "#EF4444"  # Red
                continue

            # Battery kinetics
            if agv.is_charging:
                agv.battery = min(100.0, agv.battery + 0.5 * dt)
                agv.state = "CHARGING"
                agv.color = "#3B82F6"  # Blue
                if agv.battery >= 99.0:
                    agv.is_charging = False
                    agv.state = "IDLE"
                    agv.target_x, agv.target_y = (4.0, 6.0)
                continue
            else:
                # Movement discharge
                discharge_rate = 0.02 * (agv.speed / 1.0)
                agv.battery = max(0.0, agv.battery - discharge_rate * dt)
                if agv.battery <= 0.0:
                    agv.state = "FAULT"
                    agv.safety_halt = True
                    agv.color = "#F59E0B"  # Amber
                    self._raise_alarm("ALM-BATT-01", f"{agv.id} battery depleted on active floor", "HIGH")
                    continue

            # Movement kinematics towards target
            dx = agv.target_x - agv.x
            dy = agv.target_y - agv.y
            distance = math.sqrt(dx * dx + dy * dy)

            if distance > 0.1:
                agv.state = "MOVING"
                # Move towards target at current speed limit
                agv.speed = min(agv.speed_limit, distance / dt)
                move_dist = agv.speed * dt
                agv.x += (dx / distance) * move_dist
                agv.y += (dy / distance) * move_dist
            else:
                agv.x = agv.target_x
                agv.y = agv.target_y
                agv.speed = 0.0
                agv.state = "IDLE"
                # Cycle task logic if reached station
                self._handle_agv_arrival(agv)

            # Check Zone B restricted boundary violation
            in_zone_b = self.is_in_zone_b(agv.x, agv.y)
            agv.in_restricted_zone = in_zone_b

            if in_zone_b:
                agv.color = "#F97316"  # Orange in zone
                # Hazard condition: Speed in Zone B must never exceed 0.8 m/s!
                if agv.speed > 0.8:
                    agv.safety_halt = True
                    agv.color = "#DC2626"  # Deep red
                    self.safety_sensors["SENSOR-17"].tripped = True
                    self.safety_sensors["SENSOR-17"].trip_reason = (
                        f"Overspeed in restricted Zone B ({agv.speed:.2f} m/s > 0.80 m/s limit) by {agv.id}"
                    )
                    # Interlock: Halt conveyor and drop plant throughput
                    self.conveyor.is_running = False
                    self.order_throughput_hourly = max(0.0, self.order_throughput_hourly - 80.0)
                    self._raise_alarm(
                        "ALM-ZONEB-OVERSPEED",
                        f"CRITICAL: {agv.id} triggered SENSOR-17 in Zone B. Conveyor interlocked.",
                        "CRITICAL",
                    )

        # 2. Update Conveyor
        if self.conveyor.is_running and not self.safety_sensors["SENSOR-01"].tripped:
            # Transfer boxes towards pack station
            if self.conveyor.speed_pct > 80.0:
                # Malicious or abnormal overspeed leads to box pileup/jam
                self.conveyor.boxes_on_belt += random.choice([0, 1])
                if self.conveyor.boxes_on_belt > self.conveyor.max_capacity:
                    self.conveyor.jammed = True
                    self.conveyor.is_running = False
                    self.safety_sensors["SENSOR-21"].tripped = True
                    self.safety_sensors["SENSOR-21"].trip_reason = "Conveyor box jam detected"
                    self._raise_alarm("ALM-CONV-JAM", "Conveyor buffer jam at packing station", "HIGH")
            else:
                # Normal transport
                if self.conveyor.boxes_on_belt > 0 and random.random() < 0.15:
                    self.conveyor.boxes_on_belt -= 1
                    self.completed_orders += 1
        else:
            # Conveyor halted drops throughput
            self.order_throughput_hourly = max(0.0, self.order_throughput_hourly * 0.98)

    def _handle_agv_arrival(self, agv: AGV):
        """Standard warehouse dispatch routing logic."""
        if agv.has_package:
            # Deliver to conveyor drop-off (14.0, 14.0)
            if math.isclose(agv.x, 14.0, abs_tol=0.2) and math.isclose(agv.y, 14.0, abs_tol=0.2):
                agv.has_package = False
                self.conveyor.boxes_on_belt += 1
                # Return to pick station or idle
                agv.target_x, agv.target_y = (4.0, 4.0)
            else:
                agv.target_x, agv.target_y = (14.0, 14.0)
        else:
            # Pick package from station
            if math.isclose(agv.x, 4.0, abs_tol=0.2) and math.isclose(agv.y, 14.0, abs_tol=0.2):
                agv.has_package = True
                agv.target_x, agv.target_y = (14.0, 14.0)
            elif math.isclose(agv.x, 4.0, abs_tol=0.2) and math.isclose(agv.y, 4.0, abs_tol=0.2):
                agv.target_x, agv.target_y = (4.0, 14.0)

    def _raise_alarm(self, code: str, msg: str, severity: str):
        if not any(a["code"] == code for a in self.active_alarms):
            self.active_alarms.append(
                {"code": code, "message": msg, "severity": severity, "time": self.sim_time}
            )

    def clear_alarms(self):
        self.active_alarms.clear()
        for s in self.safety_sensors.values():
            s.tripped = False
            s.trip_reason = ""
        self.conveyor.is_running = True
        self.conveyor.jammed = False
        for agv in self.agvs.values():
            agv.safety_halt = False
            agv.color = "#10B981"
        self.order_throughput_hourly = 142.0

    def get_state(self) -> Dict:
        """Serializes current cyber-physical state."""
        return {
            "sim_time": round(self.sim_time, 2),
            "agvs": {
                agv_id: {
                    "id": agv.id,
                    "name": agv.name,
                    "x": round(agv.x, 2),
                    "y": round(agv.y, 2),
                    "target_x": round(agv.target_x, 2),
                    "target_y": round(agv.target_y, 2),
                    "speed": round(agv.speed, 2),
                    "speed_limit": round(agv.speed_limit, 2),
                    "battery": round(agv.battery, 1),
                    "is_charging": agv.is_charging,
                    "state": agv.state,
                    "has_package": agv.has_package,
                    "in_restricted_zone": agv.in_restricted_zone,
                    "safety_halt": agv.safety_halt,
                    "color": agv.color,
                }
                for agv_id, agv in self.agvs.items()
            },
            "conveyor": {
                "id": self.conveyor.id,
                "name": self.conveyor.name,
                "speed_pct": round(self.conveyor.speed_pct, 1),
                "is_running": self.conveyor.is_running,
                "boxes_on_belt": self.conveyor.boxes_on_belt,
                "jammed": self.conveyor.jammed,
            },
            "sensors": {
                s_id: {
                    "id": s.id,
                    "name": s.name,
                    "zone": s.zone,
                    "tripped": s.tripped,
                    "trip_reason": s.trip_reason,
                }
                for s_id, s in self.safety_sensors.items()
            },
            "kpis": {
                "completed_orders": self.completed_orders,
                "order_throughput_hourly": round(self.order_throughput_hourly, 1),
                "active_alarm_count": len(self.active_alarms),
            },
            "alarms": self.active_alarms,
        }
