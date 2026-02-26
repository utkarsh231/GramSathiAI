import json
from pathlib import Path
from typing import Dict, Any, List

def load_schemes(path: str = "data/schemes.json") -> List[Dict[str, Any]]:
    return json.loads(Path(path).read_text(encoding="utf-8"))

def check_eligibility(user: Dict[str, Any], scheme: Dict[str, Any]) -> Dict[str, Any]:
    rules = scheme.get("rules", {})
    reasons = []
    eligible = True

    if rules.get("must_be_farmer") and not user.get("is_farmer", False):
        eligible = False
        reasons.append("User indicated they are not a farmer.")

    if rules.get("land_holding_required") and not user.get("has_land_records", False):
        eligible = False
        reasons.append("Land holding records required but not provided/confirmed.")

    missing_docs = []
    for d in scheme.get("required_documents", []):
        # simple: ask user checkbox for 2 docs; others treated missing
        if not user.get("docs", {}).get(d, False):
            missing_docs.append(d)

    confidence = 0.85 if eligible else 0.6
    if len(missing_docs) >= 2:
        confidence -= 0.2
    confidence = max(0.2, min(0.9, confidence))

    return {
        "eligible": eligible,
        "reasons": reasons,
        "missing_documents": missing_docs,
        "checklist": scheme.get("steps", []),
        "confidence": confidence
    }