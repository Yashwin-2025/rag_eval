from typing import Any, Dict, List, Tuple
import math

class CoreAlignmentService:
    @staticmethod
    def run_constitutional_ai_simulation(prompt: str, raw_answer: str) -> Dict[str, Any]:
        """Topic 4: AI alignment mechanisms (Constitutional AI Critique and Revision)
        Simulates model-in-the-loop self-critique based on safety principles.
        """
        constitution = [
            "Rule 1: The response must be polite and avoid insulting language.",
            "Rule 2: The response must be professional and objective, avoiding bias."
        ]
        
        critique = []
        revised_answer = raw_answer
        
        # Critique stage
        if "lazy" in raw_answer.lower() or "idiot" in raw_answer.lower():
            critique.append("Violates Rule 1: contains judgmental terms ('lazy' or 'idiot').")
            # Revision stage
            revised_answer = raw_answer.replace("lazy", "under-performing").replace("idiot", "individual in need of training")
            
        if "obviously" in raw_answer.lower():
            critique.append("Violates Rule 2: contains subjective/presumptuous language ('obviously').")
            revised_answer = revised_answer.replace("obviously ", "")
            
        aligned = len(critique) == 0
        return {
            "original_response": raw_answer,
            "aligned": aligned,
            "applied_constitution": constitution,
            "critique_steps": critique,
            "revised_response": revised_answer,
            "explanation": "Response revised to align with safety constitution principles." if not aligned else "Response aligned."
        }

    @staticmethod
    def simulate_differential_privacy_sgd(
        gradients: List[float], 
        clip_threshold: float = 1.0, 
        noise_multiplier: float = 0.5
    ) -> Tuple[List[float], Dict[str, Any]]:
        """Topic 20 & 30: Differential privacy (DP-SGD implementation and privacy budget tracking)
        Clips gradients and adds Gaussian noise to simulate DP-SGD, outputting dynamic epsilon (ε) growth.
        """
        # Calculate l2 norm of gradients
        l2_norm = sum(g**2 for g in gradients) ** 0.5
        
        # Clip step
        clip_factor = min(1.0, clip_threshold / max(1e-6, l2_norm))
        clipped_gradients = [g * clip_factor for g in gradients]
        
        # Noise injection step (using simple gaussian/box-muller simulation)
        # Using a deterministic random generator mockup for demonstration
        simulated_noise = []
        for i, g in enumerate(clipped_gradients):
            # Simulated pseudo-noise offset
            noise = math.sin(i + 1) * noise_multiplier * clip_threshold
            simulated_noise.append(noise)
            
        dp_gradients = [g + n for g, n in zip(clipped_gradients, simulated_noise)]
        
        # Privacy budget ε calculation mockup (Rényi Differential Privacy growth)
        # Epsilon increases inversely with noise size and directly with iterations (simulating 1 step here)
        delta = 1e-5
        epsilon = (clip_threshold ** 2) / (2 * (noise_multiplier ** 2)) + math.sqrt(2 * math.log(1.2 / delta))
        
        # Accuracy utility degradation calculation (loss increases as noise multiplier increases)
        utility_score = max(0.0, 1.0 - (noise_multiplier * 0.4))
        
        return dp_gradients, {
            "original_norm": l2_norm,
            "clipped_norm": sum(cg**2 for cg in clipped_gradients) ** 0.5,
            "noise_multiplier": noise_multiplier,
            "epsilon_consumed": round(epsilon, 3),
            "delta": delta,
            "utility_retained_score": round(utility_score * 100, 1),
            "explanation": f"DP-SGD applied. Privacy budget ε = {round(epsilon, 3)} consumed. Retained utility accuracy score: {round(utility_score * 100, 1)}%."
        }

    @staticmethod
    def analyze_proxy_discrimination(
        features_dict: Dict[str, List[Any]], 
        protected_attribute_values: List[Any]
    ) -> Dict[str, Any]:
        """Topic 32: Eliminating proxy discrimination
        Checks features for mutual correlations with protected attributes (like gender or race).
        """
        high_risk_proxies = []
        correlation_matrix = {}
        
        n = len(protected_attribute_values)
        if n == 0:
            return {"proxies_found": [], "correlation_matrix": {}}
            
        # Map protected attribute to binary numeric representation (0/1)
        unique_protected = list(set(protected_attribute_values))
        p_num = [1 if v == unique_protected[0] else 0 for v in protected_attribute_values]
        
        for feature_name, values in features_dict.items():
            if len(values) != n:
                continue
                
            # If feature values are categorical, convert to dummy indicator integers
            try:
                unique_f = list(set(values))
                f_num = [1 if v == unique_f[0] else 0 for v in values]
            except Exception:
                continue
                
            # Calculate simple Pearson correlation coefficient
            mean_p = sum(p_num) / n
            mean_f = sum(f_num) / n
            
            num = sum((p - mean_p) * (f - mean_f) for p, f in zip(p_num, f_num))
            den_p = sum((p - mean_p)**2 for p in p_num) ** 0.5
            den_f = sum((f - mean_f)**2 for f in f_num) ** 0.5
            
            if den_p == 0 or den_f == 0:
                corr = 0.0
            else:
                corr = num / (den_p * den_f)
                
            correlation_matrix[feature_name] = round(abs(corr), 3)
            
            # Threshold of 0.4 indicates proxy feature risk
            if abs(corr) >= 0.4:
                high_risk_proxies.append({
                    "feature": feature_name,
                    "correlation": round(abs(corr), 3),
                    "reason": f"High correlation with protected attribute ({round(abs(corr), 3)}) indicating proxy risk."
                })
                
        return {
            "proxies_found": high_risk_proxies,
            "correlation_matrix": correlation_matrix,
            "explanation": "Proxy Features Detected! We recommend removing flagged attributes from training." if len(high_risk_proxies) > 0 else "No proxy discrimination attributes found."
        }

    @staticmethod
    def simulate_biased_feedback_loop(
        historical_patrols: List[str], 
        retraining_generations: int = 3, 
        exploration_rate: float = 0.1
    ) -> Dict[str, Any]:
        """Topic 33: Breaking biased feedback loops
        Simulates biased prediction loop amplification and breaking it using epsilon-greedy exploration.
        """
        # Scenario: predictive policing routing patrols to Location A.
        # Loop Standard: Model sends patrols to A -> Arrests made in A -> Training data has more A -> Model locks onto A.
        # Loop Mitigated: allocation of exploration patrols (epsilon-greedy) collects unbiased base data.
        
        loop_standard = []
        loop_mitigated = []
        
        # Initial allocations
        current_standard = {"A": 0.8, "B": 0.2}
        current_mitigated = {"A": 0.8, "B": 0.2}
        
        for g in range(retraining_generations):
            # Standard loop updates: patrols match predictions, confirming bias
            a_patrols_std = current_standard["A"]
            current_standard["A"] = min(0.99, current_standard["A"] + (a_patrols_std * 0.1))
            current_standard["B"] = 1.0 - current_standard["A"]
            loop_standard.append(dict(current_standard))
            
            # Mitigated loop: force exploration patrols to collect background data
            a_patrols_mit = current_mitigated["A"] * (1 - exploration_rate) + (exploration_rate * 0.5)
            # Adjust updates using exploration probability weighting
            current_mitigated["A"] = max(0.5, current_mitigated["A"] - (exploration_rate * 0.15))
            current_mitigated["B"] = 1.0 - current_mitigated["A"]
            loop_mitigated.append(dict(current_mitigated))
            
        return {
            "iterations": retraining_generations,
            "unmitigated_bias_trend": loop_standard,
            "mitigated_bias_trend": loop_mitigated,
            "exploration_rate": exploration_rate,
            "explanation": f"Epsilon-greedy exploration ({int(exploration_rate*100)}% rate) successfully broke the reinforcing loop, bringing system selection rates back toward baseline distribution."
        }
