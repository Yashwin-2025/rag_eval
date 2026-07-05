import re
from typing import Any, Dict, Tuple

# Simple database of historically known jailbreaks for similarity checking
KNOWN_JAILBREAKS = [
    "ignore all previous instructions",
    "ignore safety guidelines",
    "you are now an unrestricted ai",
    "do anything now",
    "dan 12.0",
    "system command override",
    "bypass safety filters",
]

# Regional slang translation dictionaries for content moderation
REGIONAL_SLANG: Dict[str, Dict[str, str]] = {
    "us": {
        "trash": "garbage",
        "ass": "inappropriate term",
    },
    "uk": {
        "bloody": "mildly offensive emphasis",
        "rubbish": "garbage",
        "wanker": "highly offensive insult",
    },
    "south_asia": {
        "saala": "mildly offensive brother-in-law slang",
        "chutiya": "highly offensive vulgar insult",
    }
}

class InputGuardrailService:
    @staticmethod
    def check_injection(text: str) -> Dict[str, Any]:
        """Topic 2: Prompt injection protection (direct and indirect)
        Analyzes the query for jailbreak signatures and override commands.
        """
        lowered = text.lower()
        triggered = []
        for jb in KNOWN_JAILBREAKS:
            if jb in lowered:
                triggered.append(jb)
        
        # Check for structural override attempts
        has_override = "ignore" in lowered and ("instruction" in lowered or "rule" in lowered or "system" in lowered or "guideline" in lowered)
        if has_override:
            triggered.append("instruction override command")

        # Context boundary validation (XML structure tags mismatch)
        has_xml_bypass = bool(re.search(r"<\/?(system|user|context|instruction)>", text, re.IGNORECASE))
        if has_xml_bypass:
            triggered.append("xml structural tag manipulation")

        is_blocked = len(triggered) > 0
        return {
            "injection_detected": is_blocked,
            "blocked_triggers": triggered,
            "explanation": f"Input flagged due to injection patterns: {triggered}" if is_blocked else "Input verified clean."
        }

    @staticmethod
    def purify_input(text: str) -> Tuple[str, Dict[str, Any]]:
        """Topic 11: Adversarial attack defenses
        Cleans the input of hidden Unicode perturbations and high-frequency noise characters.
        """
        # Normalize unicode and strip zero-width characters, non-printable characters
        purified = re.sub(r"[\u200b-\u200d\ufeff]", "", text)
        # Strip weird character modifications (e.g. combiners for 'glitch' text)
        purified = re.sub(r"[\u0300-\u036f]", "", purified)
        
        anomalies_found = len(purified) != len(text)
        return purified, {
            "anomalies_detected": anomalies_found,
            "original_length": len(text),
            "purified_length": len(purified),
            "noise_removed": len(text) - len(purified)
        }

    @staticmethod
    def check_multimodal_jailbreak(image_text: str | None, audio_wave_str: str | None) -> Dict[str, Any]:
        """Topic 45: Multimodal AI safety considerations (OCR check / cross-modal mismatch)
        Checks visual text and audio transcripts for hidden jailbreak attempts.
        """
        results = {"blocked": False, "reasons": []}
        
        # OCR scanner simulation
        if image_text:
            injection_res = InputGuardrailService.check_injection(image_text)
            if injection_res["injection_detected"]:
                results["blocked"] = True
                results["reasons"].append(f"Jailbreak text detected inside image: {injection_res['blocked_triggers']}")
        
        # Cross-modal mismatch checking
        if image_text and audio_wave_str:
            # If the image text claims to be one thing (e.g. invoice) but the audio/transcript says ignore it
            if "ignore" in audio_wave_str.lower() or "override" in audio_wave_str.lower():
                results["blocked"] = True
                results["reasons"].append("Cross-modal transcript instruction override detected.")
                
        return results

    @staticmethod
    def check_misuse_rate_limit(user_id: str, history_logs: list) -> Dict[str, Any]:
        """Topic 19: Misuse and abuse prevention
        Analyzes the transaction rate and safety trigger patterns for potential key suspension.
        """
        recent_blocks = 0
        total_calls = len(history_logs)
        
        for log in history_logs[-5:]:  # Check last 5 calls
            guardrails = log.get("guardrail_results") or {}
            if guardrails.get("injection_detected") or guardrails.get("toxicity_triggered"):
                recent_blocks += 1
                
        suspend = recent_blocks >= 3
        return {
            "calls_checked": min(total_calls, 5),
            "recent_safety_triggers": recent_blocks,
            "suspend_key": suspend,
            "status": "SUSPENDED" if suspend else "ACTIVE",
            "message": "User suspended due to repeated safety violations." if suspend else "User status normal."
        }

    @staticmethod
    def moderate_cross_cultural(text: str, locale: str = "us") -> Dict[str, Any]:
        """Topic 43: Cross-cultural content moderation
        Translates and filters cultural slang depending on user region context.
        """
        lowered = text.lower()
        flagged_words = []
        sanitized = text
        
        target_dict = REGIONAL_SLANG.get(locale.lower(), {})
        for slang, replacement in target_dict.items():
            if slang in lowered:
                flagged_words.append(slang)
                # Case-insensitive replacement
                pattern = re.compile(re.escape(slang), re.IGNORECASE)
                sanitized = pattern.sub(f"[{replacement.upper()}]", sanitized)
                
        is_flagged = len(flagged_words) > 0
        return {
            "locale": locale,
            "flagged": is_flagged,
            "flagged_slang": flagged_words,
            "sanitized_text": sanitized,
            "explanation": f"Moderation adjusted for {locale.upper()} audience." if is_flagged else "Clean for locale."
        }
