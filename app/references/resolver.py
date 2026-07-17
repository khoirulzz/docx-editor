from typing import Any, Dict

def resolve_metadata(candidate: Dict[str, Any]) -> Dict[str, Any]:
    """Stub Crossref metadata resolver for M0-M2."""
    return {
        "candidate": candidate,
        "confidence": "medium",
        "resolved": False
    }
