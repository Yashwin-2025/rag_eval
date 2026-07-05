import re
from typing import Any, Dict, List

class RetrievalGuardrailService:
    @staticmethod
    def detect_hallucination(question: str, context: str, answer: str) -> Dict[str, Any]:
        """Topic 1: LLM hallucination detection and mitigation
        Calculates groundedness using text containment checks and keyword overlap.
        """
        # Split answer into sentences
        sentences = re.split(r"(?<=[.!?])\s+", answer.strip())
        grounded_count = 0
        ungrounded_sentences = []
        
        # Simple NLI simulation: each sentence should have high overlap with the context
        context_words = set(re.findall(r"\b\w+\b", context.lower()))
        
        for sent in sentences:
            if not sent.strip():
                continue
            sent_words = set(re.findall(r"\b\w+\b", sent.lower()))
            if not sent_words:
                grounded_count += 1
                continue
            
            # Remove common stop words to focus on meaningful content
            stop_words = {"is", "the", "of", "in", "and", "a", "to", "it", "that", "this", "for", "on", "with", "as", "at", "by", "an", "has", "no", "not"}
            meaningful_words = sent_words - stop_words
            
            if not meaningful_words:
                grounded_count += 1
                continue
                
            missing_words = [w for w in meaningful_words if w not in context_words]
            
            # If more than 20% of the meaningful words are missing from the context, it's flagged as hallucination
            if len(missing_words) / len(meaningful_words) > 0.2:
                ungrounded_sentences.append(sent)
            else:
                grounded_count += 1
                
        groundedness_score = grounded_count / max(1, len([s for s in sentences if s.strip()]))
        
        return {
            "groundedness_score": groundedness_score,
            "hallucination_detected": groundedness_score < 0.75,
            "ungrounded_claims": ungrounded_sentences,
            "explanation": "Answer is fully grounded." if groundedness_score >= 0.75 else "Hallucination flagged. Answer contains ungrounded sentences."
        }

    @staticmethod
    def check_copyright_overlap(answer: str, retrieved_chunks: List[str]) -> Dict[str, Any]:
        """Topic 15 & 24: Copyright and intellectual property safeguards
        Checks if the answer replicates consecutive sequences of source text.
        """
        # Excludes formatting and splits into clean lowercase words
        def get_words(text: str) -> List[str]:
            return re.findall(r"\b\w+\b", text.lower())

        ans_words = get_words(answer)
        triggered = False
        longest_match = 0
        matching_sequence = ""

        for chunk in retrieved_chunks:
            chk_words = get_words(chunk)
            if len(ans_words) < 7 or len(chk_words) < 7:
                continue

            # Sliding window of 7 words to detect verbatim copy paste
            for i in range(len(ans_words) - 6):
                window = ans_words[i : i + 7]
                for j in range(len(chk_words) - 6):
                    if chk_words[j : j + 7] == window:
                        triggered = True
                        current_match_seq = " ".join(window)
                        if len(current_match_seq) > longest_match:
                            longest_match = len(current_match_seq)
                            matching_sequence = current_match_seq
                            
        return {
            "copyright_triggered": triggered,
            "longest_verbatim_sequence": matching_sequence,
            "explanation": f"Verbatim duplication of {longest_match} characters detected: '{matching_sequence}'" if triggered else "No copyright violations detected."
        }

    @staticmethod
    def check_data_poisoning(embedding_vector: List[float], history_embeddings: List[List[float]]) -> Dict[str, Any]:
        """Topic 12 & 39: Data poisoning detection and response
        Uses Euclidean/Cosine distance analysis to detect outlier files.
        """
        if not history_embeddings:
            return {"poison_risk": "low", "anomaly_score": 0.0, "is_poisoned": False}
            
        # Calculate mean embedding
        dims = len(embedding_vector)
        mean_vector = [0.0] * dims
        for emb in history_embeddings:
            for d in range(dims):
                mean_vector[d] += emb[d]
        for d in range(dims):
            mean_vector[d] /= len(history_embeddings)
            
        # Cosine distance simulation
        dot_product = sum(a * b for a, b in zip(embedding_vector, mean_vector))
        norm_a = sum(a * a for a in embedding_vector) ** 0.5
        norm_b = sum(b * b for b in mean_vector) ** 0.5
        
        if norm_a == 0 or norm_b == 0:
            cosine_dist = 1.0
        else:
            cosine_dist = 1.0 - (dot_product / (norm_a * norm_b))
            
        is_poisoned = cosine_dist > 0.8
        return {
            "anomaly_score": float(cosine_dist),
            "is_poisoned": is_poisoned,
            "explanation": "Anomalous training sample! Flagged as data poisoning." if is_poisoned else "Statistical similarity normal."
        }

    @staticmethod
    def check_pretrained_backdoors(weights_dict: Dict[str, List[float]]) -> Dict[str, Any]:
        """Topic 38: Detecting backdoored pre-trained models
        Scans weight vectors for abnormal activation spikes or Trojan clusters.
        """
        backdoors = []
        for weight_name, values in weights_dict.items():
            # Check for extreme outlier weights (variance threshold)
            mean_val = sum(values) / len(values)
            variance = sum((x - mean_val) ** 2 for x in values) / len(values)
            
            # Simulation: backdoors usually manifest as isolated spikes in activation values
            outliers = [x for x in values if abs(x - mean_val) > 4.0 * (variance ** 0.5)]
            if len(outliers) > 0 and len(outliers) < 0.02 * len(values):
                backdoors.append({
                    "weight_tensor": weight_name,
                    "anomaly_detected": True,
                    "trigger_weight_count": len(outliers)
                })
                
        is_backdoored = len(backdoors) > 0
        return {
            "backdoor_detected": is_backdoored,
            "flagged_tensors": backdoors,
            "explanation": "Weight scan detected high-variance trigger neurons indicative of a pre-trained backdoor." if is_backdoored else "Weights verification pass: no backdoor trojans found."
        }

    @staticmethod
    def check_k_anonymity(data_rows: List[Dict[str, Any]], quasi_identifiers: List[str], k: int = 3) -> Dict[str, Any]:
        """Topic 37: Preventing re-identification attacks (k-Anonymity, l-diversity, t-closeness)
        Validates that each quasi-identifier group matches at least k records.
        """
        groups: Dict[tuple, int] = {}
        for row in data_rows:
            key = tuple(row.get(qi) for qi in quasi_identifiers)
            groups[key] = groups.get(key, 0) + 1
            
        failing_records = 0
        explanation_logs = []
        
        for key, count in groups.items():
            if count < k:
                failing_records += count
                explanation_logs.append(f"Group {dict(zip(quasi_identifiers, key))} contains only {count} rows (minimum k={k}).")
                
        passed = failing_records == 0
        return {
            "passed": passed,
            "failing_records_count": failing_records,
            "groups_checked": len(groups),
            "explanation_details": explanation_logs,
            "explanation": "K-Anonymity check passed." if passed else "Re-identification risk high! Apply generalization filters."
        }
