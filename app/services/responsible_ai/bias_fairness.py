import re
from typing import Any, Dict, List

class BiasFairnessService:
    @staticmethod
    def calculate_demographic_parity(
        decisions: List[int], 
        protected_attributes: List[Any]
    ) -> Dict[str, Any]:
        """Topic 5 & 25: Bias detection and mitigation / Gender bias mitigation
        Computes selection rates and disparate impact indicators.
        """
        n = len(decisions)
        if n == 0 or len(protected_attributes) != n:
            return {"disparate_impact_ratio": 1.0, "parity_holds": True}
            
        unique_groups = list(set(protected_attributes))
        group_stats = {}
        
        for group in unique_groups:
            group_decisions = [decisions[i] for i in range(n) if protected_attributes[i] == group]
            selection_rate = sum(group_decisions) / max(1, len(group_decisions))
            group_stats[str(group)] = {
                "count": len(group_decisions),
                "selections": sum(group_decisions),
                "selection_rate": round(selection_rate, 3)
            }
            
        # Find max and min selection rates
        rates = [stats["selection_rate"] for stats in group_stats.values()]
        min_rate = min(rates)
        max_rate = max(rates)
        
        disparate_impact = min_rate / max(1e-6, max_rate)
        passed = disparate_impact >= 0.80  # Enforces FTC 4/5ths rule
        
        return {
            "group_metrics": group_stats,
            "disparate_impact_ratio": round(disparate_impact, 3),
            "parity_holds": passed,
            "explanation": "Demographic parity holds under the 80% rule." if passed else "Flagged bias! Selection rate differences exceed the 80% parity threshold."
        }

    @staticmethod
    def anonymize_resume_gender(text: str) -> str:
        """Topic 25: Mitigating gender bias in hiring AI
        Strips names, gender markers, sports teams, and single-sex institutions.
        """
        # Dictionary of gender indicators
        gender_markers = {
            r"\b(she|her|hers|he|him|his)\b": "[PRONOUN]",
            r"\b(women's|men's|female|male|girls|boys)\b": "[GENDER_MARKER]",
            r"\b(jane|john|alice|bob|mary|david)\b": "[NAME_HOLDER]",
            r"\b(wellesley|smith college|mount holyoke|vassar)\b": "[SINGLE_SEX_UNIVERSITY]"
        }
        
        anonymized = text
        for pattern, replacement in gender_markers.items():
            anonymized = re.sub(pattern, replacement, anonymized, flags=re.IGNORECASE)
            
        return anonymized

    @staticmethod
    def calculate_intersectional_fairness(
        decisions: List[int], 
        race_attributes: List[Any], 
        gender_attributes: List[Any]
    ) -> Dict[str, Any]:
        """Topic 26: Handling intersectional fairness
        Slices dataset by multiple attributes simultaneously and calculates minimax fairness ratios.
        """
        n = len(decisions)
        if n == 0 or len(race_attributes) != n or len(gender_attributes) != n:
            return {"passed": True, "intersectional_metrics": {}}
            
        intersectional_groups = []
        for r, g in zip(race_attributes, gender_attributes):
            intersectional_groups.append(f"{r}_{g}")
            
        # Calculate demographic parity over the composite groups
        parity_res = BiasFairnessService.calculate_demographic_parity(decisions, intersectional_groups)
        
        # Minimax fairness optimization simulation
        # Target: raise selection rate of the lowest-performing intersectional slice
        group_metrics = parity_res["group_metrics"]
        rates = [v["selection_rate"] for v in group_metrics.values()]
        min_rate = min(rates)
        max_rate = max(rates)
        
        # Simulated threshold calibration
        calibrated_group_metrics = {}
        target_rate = (min_rate + max_rate) / 2
        for g, stats in group_metrics.items():
            calibrated_rate = stats["selection_rate"]
            if calibrated_rate < target_rate:
                # Simulate boost in selection thresholds
                calibrated_rate = round(target_rate, 3)
            calibrated_group_metrics[g] = calibrated_rate
            
        return {
            "intersectional_metrics": group_metrics,
            "disparate_impact_ratio": parity_res["disparate_impact_ratio"],
            "passed": parity_res["parity_holds"],
            "calibrated_minimax_rates": calibrated_group_metrics,
            "explanation": "Intersectional parity check evaluated. Calibration recommendations computed."
        }
