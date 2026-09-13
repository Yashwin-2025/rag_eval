"""
AETHER-OT: Unsupervised ML Process Anomaly Watchdog
Uses Scikit-Learn Isolation Forest and residual drift analysis to detect subtle cyber-physical deviations (<80 MB RAM).
"""

from typing import Dict, List, Tuple, Optional
import numpy as np
from sklearn.ensemble import IsolationForest
from aether_ot.monitoring.tracer import CyberPhysicalTracer


class ProcessAnomalyWatchdog:
    """
    Evaluates multivariate warehouse telemetry vectors:
    [agv1_speed, agv2_speed, agv3_speed, conv_speed, agv1_batt, agv2_batt]
    """

    def __init__(self, contamination: float = 0.05):
        self.feature_names = [
            "agv1_speed", "agv2_speed", "agv3_speed",
            "conv_speed", "agv1_batt", "agv2_batt"
        ]
        self.model = IsolationForest(
            n_estimators=50,
            contamination=contamination,
            random_state=42,
            n_jobs=1  # Lightweight on 8GB RAM
        )
        self.is_fitted = False
        self._bootstrap_baseline()

    def _bootstrap_baseline(self):
        """Generates 300 normal operational baseline vectors for immediate model readiness."""
        np.random.seed(42)
        n_samples = 300
        # Normal AGV speed ~1.0 +/- 0.1 m/s, Conveyor ~40% +/- 5%, Battery 80-100%
        agv1_speed = np.random.normal(1.0, 0.08, n_samples)
        agv2_speed = np.random.normal(1.0, 0.08, n_samples)
        agv3_speed = np.random.normal(1.0, 0.08, n_samples)
        conv_speed = np.random.normal(40.0, 3.0, n_samples)
        agv1_batt = np.random.uniform(70.0, 100.0, n_samples)
        agv2_batt = np.random.uniform(70.0, 100.0, n_samples)

        X_train = np.column_stack([
            agv1_speed, agv2_speed, agv3_speed,
            conv_speed, agv1_batt, agv2_batt
        ])
        self.model.fit(X_train)
        self.is_fitted = True

    def extract_vector(self, state: Dict) -> np.ndarray:
        agvs = state["agvs"]
        conv = state["conveyor"]
        return np.array([
            agvs["AGV-01"]["speed"],
            agvs["AGV-02"]["speed"],
            agvs["AGV-03"]["speed"],
            conv["speed_pct"],
            agvs["AGV-01"]["battery"],
            agvs["AGV-02"]["battery"]
        ]).reshape(1, -1)

    def evaluate(self, state: Dict) -> Dict:
        """
        Evaluates current warehouse state.
        Returns anomaly_score (0.0 to 1.0), is_anomaly (bool), and top_contributor tag.
        """
        if not self.is_fitted:
            self._bootstrap_baseline()

        X = self.extract_vector(state)
        # decision_function returns negative values for anomalies, positive for inliers
        raw_score = self.model.decision_function(X)[0]
        # Normalize into [0.0, 1.0] where 1.0 is severe anomaly
        # Typically raw_score is between -0.3 (severe) and +0.25 (normal)
        normalized_anomaly_score = float(np.clip(1.0 - (raw_score + 0.3) / 0.55, 0.0, 1.0))
        is_anomaly = normalized_anomaly_score >= 0.65

        # Feature residual attribution
        contributors = []
        agvs = state["agvs"]
        conv = state["conveyor"]

        if agvs["AGV-01"]["speed"] > 1.4:
            contributors.append(f"AGV-01 Speed Overrun ({agvs['AGV-01']['speed']:.2f} m/s)")
        if agvs["AGV-02"]["speed"] > 1.4:
            contributors.append(f"AGV-02 Speed Overrun ({agvs['AGV-02']['speed']:.2f} m/s)")
        if agvs["AGV-03"]["speed"] > 1.4:
            contributors.append(f"AGV-03 Speed Overrun ({agvs['AGV-03']['speed']:.2f} m/s)")
        if conv["speed_pct"] > 75.0:
            contributors.append(f"Conveyor Motor Overspeed ({conv['speed_pct']:.1f}%)")
        if agvs["AGV-02"]["in_restricted_zone"]:
            contributors.append("AGV-02 Zone B Boundary Crossing")

        top_contributor = ", ".join(contributors) if contributors else "Statistical Latent Drift"

        # Instrument OTel trace if anomalous
        if is_anomaly:
            CyberPhysicalTracer.record_physical_anomaly(
                asset_id=top_contributor,
                metric="anomaly_score",
                value=round(normalized_anomaly_score, 3),
                threshold=0.65
            )

        return {
            "anomaly_score": round(normalized_anomaly_score, 3),
            "is_anomaly": is_anomaly,
            "top_contributor": top_contributor,
            "raw_vector": X.tolist()[0]
        }
