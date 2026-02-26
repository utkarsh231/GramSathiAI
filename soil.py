import re
from typing import Dict, Any

def parse_soil_text(text: str) -> Dict[str, Any]:
    """
    Very lightweight parser for demo.
    Looks for patterns like: pH 6.8, N 120 kg/ha, P 18 kg/ha, K 210 kg/ha
    """
    def find_float(patterns):
        for pat in patterns:
            m = re.search(pat, text, flags=re.IGNORECASE)
            if m:
                return float(m.group(1))
        return None

    ph = find_float([r"pH\s*[:\-]?\s*([0-9]+(?:\.[0-9]+)?)"])
    n  = find_float([r"\bN\b\s*[:\-]?\s*([0-9]+(?:\.[0-9]+)?)", r"Nitrogen\s*[:\-]?\s*([0-9]+(?:\.[0-9]+)?)"])
    p  = find_float([r"\bP\b\s*[:\-]?\s*([0-9]+(?:\.[0-9]+)?)", r"Phosph(?:orus)?\s*[:\-]?\s*([0-9]+(?:\.[0-9]+)?)"])
    k  = find_float([r"\bK\b\s*[:\-]?\s*([0-9]+(?:\.[0-9]+)?)", r"Potassium\s*[:\-]?\s*([0-9]+(?:\.[0-9]+)?)"])

    return {"pH": ph, "N": n, "P": p, "K": k}

def fertilizer_plan(parsed: Dict[str, Any]) -> Dict[str, Any]:
    ph, n, p, k = parsed.get("pH"), parsed.get("N"), parsed.get("P"), parsed.get("K")

    missing = [key for key, val in parsed.items() if val is None]
    confidence = 0.9 - 0.2 * len(missing)  # crude demo scoring
    confidence = max(0.2, min(0.9, confidence))

    steps = []
    if ph is not None:
        if ph < 5.5:
            steps.append("Soil pH is acidic. Consider liming after confirming with local KVK.")
        elif ph > 8.0:
            steps.append("Soil pH is alkaline. Monitor micronutrients and consult KVK for amendments.")
        else:
            steps.append("Soil pH looks within a typical range for many crops (confirm crop-specific needs).")
    else:
        steps.append("pH not found in report — please share pH value or upload clearer report.")

    def bucket(val):
        if val is None: return None
        if val < 140: return "low"
        if val < 280: return "medium"
        return "high"

    n_b, p_b, k_b = bucket(n), bucket(p), bucket(k)
    if n_b: steps.append(f"Nitrogen appears {n_b}.")
    if p_b: steps.append(f"Phosphorus appears {p_b}.")
    if k_b: steps.append(f"Potassium appears {k_b}.")

    schedule = [
        {"when": "Basal dose", "action": "Apply recommended P & K sources (e.g., SSP/DAP, MOP) as per local guidance."},
        {"when": "After 20–25 days", "action": "Split nitrogen application (e.g., urea) if needed."},
        {"when": "After 40–45 days", "action": "Second split nitrogen application if crop requires it."},
    ]

    return {
        "confidence": confidence,
        "missing_fields": missing,
        "summary": "Draft fertilizer plan (demo) generated from detected values. Validate locally before acting.",
        "steps": steps,
        "schedule": schedule
    }