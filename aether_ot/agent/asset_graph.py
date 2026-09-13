"""
AETHER-OT: Cyber-Physical Asset Dependency & Blast-Radius Graph
Uses NetworkX to model physical topology, electrical interlocks, and industrial network conduits.
"""

from typing import Dict, List, Set
import networkx as nx


class WarehouseAssetGraph:
    def __init__(self):
        self.graph = nx.DiGraph()
        self._build_graph()

    def _build_graph(self):
        # 1. Cyber Network Layer (Level 2/3)
        self.graph.add_node("OT-SW-01", type="network_switch", zone="Level 2 iDMZ", ip="10.0.0.1")
        self.graph.add_node("EWS-01", type="workstation", zone="Level 3 Operations", ip="10.0.0.10")
        self.graph.add_node("ROBOT-ROUTER", type="wireless_ap", zone="Level 1 Floor", ip="10.0.0.50")

        # 2. Industrial Controllers (Level 1)
        self.graph.add_node("PLC-01", type="plc", name="AGV Fleet Controller", ip="10.0.0.11", protocol="Modbus TCP:5020")
        self.graph.add_node("PLC-02", type="plc", name="Conveyor & Safety Controller", ip="10.0.0.12", protocol="Modbus TCP:5020")

        # 3. Physical Actuators & Robots (Level 0)
        self.graph.add_node("AGV-01", type="agv", name="Forklift-01", safety_speed_limit=1.2)
        self.graph.add_node("AGV-02", type="agv", name="Tugger-02", safety_speed_limit=1.2)
        self.graph.add_node("AGV-03", type="agv", name="Lifter-03", safety_speed_limit=1.2)
        self.graph.add_node("CONV-01", type="conveyor", name="Main Intake Conveyor", max_safe_speed=80.0)

        # 4. Spatial Zones & Safety Sensors
        self.graph.add_node("ZONE-B", type="hazard_zone", name="Restricted Lifter Zone", max_speed=0.8)
        self.graph.add_node("SENSOR-17", type="safety_interlock", name="Zone-B Laser Guard", target="CONV-01")

        # Conduits and Dependencies
        self.graph.add_edge("OT-SW-01", "PLC-01", relation="network_conduit", protocol="Modbus TCP")
        self.graph.add_edge("OT-SW-01", "PLC-02", relation="network_conduit", protocol="Modbus TCP")
        self.graph.add_edge("ROBOT-ROUTER", "PLC-01", relation="wireless_fieldbus")

        self.graph.add_edge("PLC-01", "AGV-01", relation="controls_motion", register="40001")
        self.graph.add_edge("PLC-01", "AGV-02", relation="controls_motion", register="40002")
        self.graph.add_edge("PLC-01", "AGV-03", relation="controls_motion", register="40003")

        self.graph.add_edge("PLC-02", "CONV-01", relation="controls_motor", register="40004")
        self.graph.add_edge("AGV-02", "ZONE-B", relation="can_enter")
        self.graph.add_edge("ZONE-B", "SENSOR-17", relation="monitored_by")
        self.graph.add_edge("SENSOR-17", "CONV-01", relation="hardwired_e_stop_interlock")
        self.graph.add_edge("SENSOR-17", "PLC-02", relation="signals_alarm_register", register="00003")

    def get_blast_radius(self, source_asset: str) -> Dict[str, List[str]]:
        """
        Computes the cascading physical and cyber impact if source_asset is compromised or faulted.
        """
        if source_asset not in self.graph:
            return {"direct_dependents": [], "cascade_impacts": []}

        # Descendants in dependency tree
        descendants = list(nx.descendants(self.graph, source_asset))
        direct_children = list(self.graph.successors(source_asset))

        # Explain the causal chain
        chain = []
        for node in descendants:
            node_data = self.graph.nodes[node]
            chain.append(f"{node} ({node_data.get('type', 'asset')})")

        return {
            "source_asset": source_asset,
            "direct_dependents": direct_children,
            "cascade_impacts": chain,
        }

    def explain_chain(self, start_asset: str, target_asset: str) -> List[str]:
        """Returns shortest path of physical/cyber interaction between two assets."""
        try:
            path = nx.shortest_path(self.graph, start_asset, target_asset)
            steps = []
            for i in range(len(path) - 1):
                edge_data = self.graph.get_edge_data(path[i], path[i + 1])
                steps.append(f"{path[i]} --[{edge_data.get('relation', 'connected')}]--> {path[i + 1]}")
            return steps
        except nx.NetworkXNoPath:
            return ["No direct connection found."]
