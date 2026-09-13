"""
Unit tests for AETHER-OT 2D Warehouse Physical Simulation
"""
import pytest
from aether_ot.simulator.warehouse_sim import WarehouseSimulator


def test_warehouse_init():
    sim = WarehouseSimulator()
    state = sim.get_state()
    assert len(state["agvs"]) == 3
    assert state["conveyor"]["is_running"] is True
    assert state["kpis"]["active_alarm_count"] == 0


def test_agv_movement_and_tick():
    sim = WarehouseSimulator()
    agv = sim.agvs["AGV-01"]
    initial_y = agv.y
    agv.target_y = 10.0
    agv.speed_limit = 1.0

    # Advance 10 ticks (1 second)
    for _ in range(10):
        sim.tick(dt=0.1)

    assert agv.y > initial_y
    assert agv.speed > 0.0


def test_restricted_zone_violation():
    sim = WarehouseSimulator()
    agv = sim.agvs["AGV-02"]
    # Teleport AGV-02 into Zone B with overspeed (1.5 m/s > 0.8 m/s limit)
    agv.x = 14.0
    agv.y = 6.0
    agv.target_x = 16.0
    agv.target_y = 8.0
    agv.speed = 1.5
    agv.speed_limit = 1.5

    sim.tick(dt=0.1)

    # SENSOR-17 must trip and conveyor must halt
    assert sim.safety_sensors["SENSOR-17"].tripped is True
    assert sim.conveyor.is_running is False
    assert agv.safety_halt is True
    assert len(sim.active_alarms) > 0
