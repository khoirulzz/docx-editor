from typing import Any, Dict, List

def process_reference_intake(session_id: str, assets: List[str]) -> Dict[str, Any]:
    """
    Stub implementation for reference intake (Milestone 0-2).
    In Milestone 4, this will parse loose notes, BibTeX, RIS, run deduplication and Crossref resolving.
    """
    return {
        "total": 0,
        "ready": 0,
        "ambiguous": 0,
        "unresolved": 0,
        "references": [],
        "evidence": []
    }
