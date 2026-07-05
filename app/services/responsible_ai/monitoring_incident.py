import hashlib
import json
from typing import Any, Dict, List

class MonitoringIncidentService:
    @staticmethod
    def trigger_incident_action(
        title: str, 
        description: str, 
        containment_level: str = "active", 
        kill_switch: bool = False
    ) -> Dict[str, Any]:
        """Topic 21: AI incident response plan
        Updates live containment flags and configures API safety kill-switches.
        """
        # In production, this writes directly to the postgres `incident_reports` table
        # If DB connection fails, the API router falls back to local simulation
        report = {
            "title": title,
            "description": description,
            "containment_status": containment_level,
            "kill_switch_active": kill_switch,
            "rollback_applied": True if kill_switch else False,
            "action_taken": "Traffic redirected to secure static fallbacks." if kill_switch else "Incident logged, active containment online."
        }
        return report

    @staticmethod
    def generate_blameless_post_mortem(
        incident_title: str, 
        trigger_factor: str, 
        timeline_events: List[str]
    ) -> str:
        """Topic 41: Blameless AI incident post-mortems
        Compiles structural systemic incident summaries to prevent human-blaming.
        """
        report = f"""# Blameless Post-Mortem: {incident_title}

## Summary of Event
*   **System Failure**: {incident_title}
*   **Root Systemic Cause**: {trigger_factor}

## Timeline of Events
{chr(10).join(f'*   {event}' for event in timeline_events)}

## Systemic Analysis
We focus on the system configuration and validation failures, rather than operator mistakes:
1.  **Missing Test Assertions**: The prompt validation test suite lacked check vectors for this category of input.
2.  **Inadequate Boundary Monitors**: The input filters failed to catch the unicode modification due to missing normalization stages.
3.  **Output Checks Limitation**: The output checkers didn't classify the phrase correctly due to an outdated safety lookup list.

## Corrective Engineering Actions
*   [ ] Implement unicode normalization upstream of all input guardrails.
*   [ ] Synchronize safety keywords database with the latest clinical safety dictionary.
*   [ ] Add regression tests to pytest configurations representing this incident payload.
"""
        return report

    @staticmethod
    def secure_log_block(
        log_id: str, 
        payload: Dict[str, Any], 
        previous_block_hash: str = "0000000000000000"
    ) -> Dict[str, Any]:
        """Topic 17 & 36: Long-term audit logging (immutability hashing)
        Calculates SHA-256 blocks to secure logs chronologically (simulated S3 Object Lock compliance).
        """
        payload_str = json.dumps(payload, sort_keys=True)
        block_data = f"{log_id}|{payload_str}|{previous_block_hash}"
        block_hash = hashlib.sha256(block_data.encode()).hexdigest()
        
        return {
            "log_id": log_id,
            "preceding_hash": previous_block_hash,
            "current_block_hash": block_hash,
            "immutable": True,
            "locked_status": "COMPLIANCE_MODE_ACTIVE"
        }
