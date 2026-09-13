"""
AETHER-OT: Industrial Modbus TCP Server & PLC Memory Interface
Maps simulated cyber-physical warehouse states to standard IEC Modbus registers.
"""

import asyncio
import logging
from typing import Optional
from pymodbus.datastore import (
    ModbusSequentialDataBlock,
    ModbusServerContext,
    ModbusDeviceContext,
)
from pymodbus.server import StartAsyncTcpServer
from aether_ot.simulator.warehouse_sim import WarehouseSimulator

logger = logging.getLogger("aether_ot.modbus")


class ModbusPLCBridge:
    """
    Bridges WarehouseSimulator state with Modbus TCP Holding Registers and Coils.
    
    Holding Registers (40001+):
    - 40001: AGV-01 Speed Setpoint (m/s * 100)
    - 40002: AGV-02 Speed Setpoint (m/s * 100)
    - 40003: AGV-03 Speed Setpoint (m/s * 100)
    - 40004: Conveyor Motor Speed Setpoint (%)
    - 40005: AGV-01 Battery (% * 10)
    - 40006: AGV-02 Battery (% * 10)
    - 40007: AGV-03 Battery (% * 10)
    - 40008: Active Alarm Count
    - 40009: AGV-01 X-Coord (meters * 100)
    - 40010: AGV-01 Y-Coord (meters * 100)
    - 40011: AGV-02 X-Coord (meters * 100)
    - 40012: AGV-02 Y-Coord (meters * 100)
    
    Discrete Coils (00001+):
    - 00001: Master E-Stop (1 = Active)
    - 00002: Conveyor Run Command (1 = Running, 0 = Stopped)
    - 00003: SENSOR-17 Tripped Status (1 = Tripped)
    - 00004: AGV-01 Charge Enable (1 = Normal, 0 = Disabled)
    - 00005: AGV-02 Charge Enable
    - 00006: AGV-03 Charge Enable
    """

    def __init__(self, simulator: WarehouseSimulator, host: str = "127.0.0.1", port: int = 5020):
        self.simulator = simulator
        self.host = host
        self.port = port
        self.running = False
        self.server_task: Optional[asyncio.Task] = None

        # Modbus block initial values
        # 100 registers each to avoid boundary errors
        hr_block = ModbusSequentialDataBlock(1, [
            100,  # 40001: AGV-01 1.00 m/s
            100,  # 40002: AGV-02 1.00 m/s
            100,  # 40003: AGV-03 1.00 m/s
            40,   # 40004: Conveyor 40%
            1000, # 40005: AGV-01 100.0%
            1000, # 40006: AGV-02 100.0%
            1000, # 40007: AGV-03 100.0%
            0,    # 40008: Alarms
            400,  # 40009: AGV-01 X
            400,  # 40010: AGV-01 Y
            800,  # 40011: AGV-02 X
            400,  # 40012: AGV-02 Y
        ] + [0] * 88)

        coils_block = ModbusSequentialDataBlock(1, [
            0, # 00001: E-Stop
            1, # 00002: Conveyor Run
            0, # 00003: Sensor-17 Tripped
            1, # 00004: AGV-01 Charge Enable
            1, # 00005: AGV-02 Charge Enable
            1, # 00006: AGV-03 Charge Enable
        ] + [0] * 94)

        self.device_context = ModbusDeviceContext(
            di=ModbusSequentialDataBlock(1, [0] * 100),
            co=coils_block,
            hr=hr_block,
            ir=ModbusSequentialDataBlock(1, [0] * 100),
        )
        self.context = ModbusServerContext(devices=self.device_context, single=True)

        # Direct memory access buffers (0-indexed)
        # Register 40001 is index 0, 40002 is index 1, etc.
        self.hr_values = self.device_context.simdevice.simdata[2][0].values
        self.co_values = self.device_context.simdevice.simdata[1][0].values

    def sync_from_simulator(self):
        """Copies real-time physics variables into Modbus registers."""
        state = self.simulator.get_state()
        agv1 = state["agvs"]["AGV-01"]
        agv2 = state["agvs"]["AGV-02"]
        agv3 = state["agvs"]["AGV-03"]
        conv = state["conveyor"]
        s17 = state["sensors"]["SENSOR-17"]

        # Update telemetry registers
        # Index 4 (40005) = AGV-01 Battery
        self.hr_values[4] = int(agv1["battery"] * 10)
        self.hr_values[5] = int(agv2["battery"] * 10)
        self.hr_values[6] = int(agv3["battery"] * 10)
        self.hr_values[7] = state["kpis"]["active_alarm_count"]
        self.hr_values[8] = int(agv1["x"] * 100)
        self.hr_values[9] = int(agv1["y"] * 100)
        self.hr_values[10] = int(agv2["x"] * 100)
        self.hr_values[11] = int(agv2["y"] * 100)

        # Update coils
        # Index 1 (00002) = Conveyor Running
        # Index 2 (00003) = SENSOR-17 Tripped
        self.co_values[1] = bool(conv["is_running"])
        self.co_values[2] = bool(s17["tripped"])

    def sync_to_simulator(self):
        """Reads setpoint registers written by Modbus clients/attackers and updates simulator."""
        # Read speed setpoints (Registers 40001, 40002, 40003 -> indices 0, 1, 2)
        self.simulator.agvs["AGV-01"].speed_limit = self.hr_values[0] / 100.0
        self.simulator.agvs["AGV-02"].speed_limit = self.hr_values[1] / 100.0
        self.simulator.agvs["AGV-03"].speed_limit = self.hr_values[2] / 100.0

        # Read conveyor speed setpoint (Register 40004 -> index 3)
        self.simulator.conveyor.speed_pct = float(self.hr_values[3])

        # Read coils
        # Coil 1 (index 0) = E-Stop
        if self.co_values[0]:
            self.simulator.safety_sensors["SENSOR-01"].tripped = True
            self.simulator.conveyor.is_running = False
            for agv in self.simulator.agvs.values():
                agv.safety_halt = True

        # Coil 2 (index 1) = Conveyor Run/Stop
        if not self.co_values[1]:
            self.simulator.conveyor.is_running = False

    async def run_server(self):
        """Starts Modbus TCP server asynchronously."""
        logger.info(f"Starting Modbus TCP PLC Server on {self.host}:{self.port}")
        self.running = True
        await StartAsyncTcpServer(
            context=self.context,
            address=(self.host, self.port),
        )
