import re
from typing import Any, Dict, List

class OutputGuardrailService:
    @staticmethod
    def validate_schema_format(text: str, expected_fields: List[str]) -> Dict[str, Any]:
        """Topic 3: Output structural guardrails
        Checks if output parses correctly according to schema specifications.
        """
        import json
        try:
            parsed = json.loads(text)
            missing = [f for f in expected_fields if f not in parsed]
            if len(missing) > 0:
                return {"valid": False, "error": f"Missing schema fields: {missing}", "parsed": parsed}
            return {"valid": True, "error": None, "parsed": parsed}
        except json.JSONDecodeError as e:
            return {"valid": False, "error": f"JSON decode failed: {str(e)}", "parsed": None}

    @staticmethod
    def check_toxicity(text: str) -> Dict[str, Any]:
        """Topic 13: Content safety filtering
        Flags toxic, hateful, or inappropriate sequences.
        """
        bad_words = ["idiot", "jerk", "fuck", "kill yourself", "die", "hate you"]
        lowered = text.lower()
        triggered_words = []
        
        for word in bad_words:
            if word in lowered:
                triggered_words.append(word)
                
        is_toxic = len(triggered_words) > 0
        return {
            "toxic": is_toxic,
            "triggered_words": triggered_words,
            "toxicity_score": 0.95 if is_toxic else 0.05,
            "explanation": "Safety filter blocked response: toxic content detected." if is_toxic else "Clean output text."
        }

    @staticmethod
    def check_medical_intent(text: str) -> Dict[str, Any]:
        """Topic 23: Healthcare chatbot safety guardrails
        Intercepts unsolicited diagnostic attempts and clinical prescriptions.
        """
        diagnostic_indicators = [
            "you have", "diagnose", "suffering from", "prescribe", 
            "take this medicine", "treatment for", "clinical condition"
        ]
        lowered = text.lower()
        triggered = [phrase for phrase in diagnostic_indicators if phrase in lowered]
        
        has_medical = len(triggered) > 0
        disclaimer = (
            "I am an AI assistant, not a doctor. I cannot provide medical diagnoses, "
            "treatment recommendations, or prescriptions. Please consult a qualified "
            "healthcare professional."
        )
        return {
            "medical_advice_detected": has_medical,
            "triggered_phrases": triggered,
            "disclaimer_response": disclaimer,
            "explanation": "Medical diagnostic advice intercepted and replaced with safety disclaimer." if has_medical else "Safe chat response."
        }

    @staticmethod
    def check_mental_health_crisis(text: str) -> Dict[str, Any]:
        """Topic 40: Mental health chatbot crisis safety
        Scans inputs and outputs for self-harm or suicide crisis triggers.
        """
        crisis_terms = [
            "suicide", "kill myself", "end my life", "want to die", 
            "hurt myself", "self harm", "no reason to live"
        ]
        lowered = text.lower()
        triggered = [term for term in crisis_terms if term in lowered]
        
        is_crisis = len(triggered) > 0
        crisis_card = {
            "message": "It sounds like you are going through a difficult time. Please know you are not alone and help is available.",
            "resources": [
                {"name": "Suicide & Crisis Lifeline", "contact": "Call or Text 988", "availability": "24/7, Free, Confidential"},
                {"name": "Crisis Text Line", "contact": "Text HOME to 741741", "availability": "24/7 text support"}
            ]
        }
        return {
            "crisis_detected": is_crisis,
            "triggered_terms": triggered,
            "crisis_response_card": crisis_card,
            "explanation": "Crisis trigger detected upstream. Emergency helpline resources returned." if is_crisis else "Normal status."
        }

    @staticmethod
    def apply_overreliance_mitigation(text: str, confidence_score: float = 0.65) -> Dict[str, Any]:
        """Topic 42: Preventing human over-reliance on AI recommendations
        Injects cognitive friction (low confidence indicators, multiple choices).
        """
        alert_needed = confidence_score < 0.80
        warning_msg = (
            f"Attention: The model confidence is low ({int(confidence_score*100)}%). "
            "Please verify the source documents before acting on this advice."
        )
        
        # Simulated alternative choices
        alternative_options = [
            "Option A (Highest Probable Match)",
            "Option B (Alternative Interpretation)"
        ]
        
        return {
            "confidence": confidence_score,
            "requires_friction_block": alert_needed,
            "warning_message": warning_msg if alert_needed else None,
            "alternative_hypotheses": alternative_options,
            "explanation": "Friction block active: user prompted to review choices before accepting AI advice." if alert_needed else "High confidence advice."
        }

    @staticmethod
    def embed_watermark(text: str, image_bytes_count: int | None = None) -> Dict[str, Any]:
        """Topic 34: Watermarking AI-generated images/content
        Injects hidden validation signatures in generated text (zero-width spaces) or images (cryptographic C2PA header tags).
        """
        # Inject zero-width space sequence representing "AI-GEN" in text
        # zero-width spaces: \u200b
        signature = "\u200b\u200b\u200c\u200b"
        watermarked_text = text + signature
        
        # Verify watermark presence
        extracted_sig = "\u200b\u200b\u200c\u200b" in watermarked_text
        
        results = {
            "text_watermarked": True,
            "watermarked_response": watermarked_text,
            "watermark_verified": extracted_sig,
        }
        
        # Image C2PA manifestation simulation
        if image_bytes_count:
            results["c2pa_manifest_injected"] = True
            results["c2pa_metadata"] = {
                "producer": "AI Safety & Responsible RAG platform",
                "model": "gpt-4o-mini",
                "signature": "SHA256withRSA:5f7e...",
                "timestamp": "2026-07-05T22:00:00Z"
            }
            
        return results
