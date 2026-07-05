import re
from difflib import SequenceMatcher

def scrub_pii(text: str) -> tuple[str, dict[str, str]]:
    """Redacts PII (emails, phone numbers, SSNs) and returns the scrubbed text and redaction mapping."""
    email_pattern = r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"
    # Matches common phone number formats
    phone_pattern = r"\b(?:\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b"
    ssn_pattern = r"\b\d{3}-\d{2}-\d{4}\b"

    mapping = {}
    scrubbed = text

    # Helper function to replace matches and populate mapping
    def replace_pattern(pattern, placeholder_prefix, content):
        count = 1
        current_text = content
        while True:
            match = re.search(pattern, current_text)
            if not match:
                break
            original = match.group(0)
            placeholder = f"[{placeholder_prefix}_{count}]"
            mapping[placeholder] = original
            current_text = current_text.replace(original, placeholder, 1)
            count += 1
        return current_text

    scrubbed = replace_pattern(email_pattern, "EMAIL", scrubbed)
    scrubbed = replace_pattern(phone_pattern, "PHONE", scrubbed)
    scrubbed = replace_pattern(ssn_pattern, "SSN", scrubbed)

    return scrubbed, mapping


def check_injection(text: str) -> bool:
    """Returns True if user input contains prompt injection attempt indicators."""
    jailbreak_keywords = [
        "ignore previous instructions",
        "ignore all previous instructions",
        "system prompt",
        "you are now",
        "ignore safety",
        "jailbreak",
        "overwrite instructions",
        "do not follow",
    ]
    lowered = text.lower()
    for kw in jailbreak_keywords:
        if kw in lowered:
            return True
    return False


def _get_words(t: str) -> list[str]:
    """Helper to extract clean lowercase words."""
    return re.findall(r"\b\w+\b", t.lower())


def check_verbatim_overlap(answer: str, chunks: list[str]) -> bool:
    """Returns True if the generated answer copies 7 or more consecutive words from any source chunk.
    
    This is an intellectual property/copyright protection mechanism.
    """
    ans_words = _get_words(answer)
    if len(ans_words) < 7:
        return False

    for chunk in chunks:
        chk_words = _get_words(chunk)
        if len(chk_words) < 7:
            continue
        
        # Check for consecutive word subsequences of length 7
        for i in range(len(ans_words) - 6):
            subseq = ans_words[i : i + 7]
            for j in range(len(chk_words) - 6):
                if chk_words[j : j + 7] == subseq:
                    return True
    return False


def check_medical_safety(answer: str) -> bool:
    """Returns True if the response contains unsolicited medical diagnosis/treatment recommendations."""
    diagnostic_phrases = [
        "you have",
        "diagnose you with",
        "treatment for your",
        "take this medicine",
        "prescription for",
        "medical condition",
        "you are suffering from",
        "diagnosed with",
    ]
    lowered = answer.lower()
    for phrase in diagnostic_phrases:
        if phrase in lowered:
            return True
    return False
