from typing import Any, Dict, List
from app.models.domain import DocumentGraph, VerificationLevelResult, VerificationStatus

class CitationIntegrityVerifier:
    """
    L5 Citation and Protected Field Verification.
    Ensures that every protected field (Mendeley citations/bibliography, TOC)
    present in base document retains its exact fingerprint and structure in the proposal.
    """
    @staticmethod
    def verify(base_graph: DocumentGraph, proposal_graph: DocumentGraph) -> VerificationLevelResult:
        checks: List[Dict[str, Any]] = []
        
        base_protected = {
            f["field_id"]: f
            for f in base_graph.fields
            if f.get("is_protected", False)
        }
        
        proposal_protected = {
            f["field_id"]: f
            for f in proposal_graph.fields
            if f.get("is_protected", False)
        }

        all_passed = True
        for fid, b_fld in base_protected.items():
            if fid not in proposal_protected:
                all_passed = False
                checks.append({
                    "check": "protected_field_existence",
                    "status": "FAIL",
                    "detail": f"Protected field '{fid}' ({b_fld.get('field_type')}) was deleted or missing in proposal."
                })
                continue
                
            p_fld = proposal_protected[fid]
            if b_fld.get("fingerprint_sha256") != p_fld.get("fingerprint_sha256"):
                all_passed = False
                checks.append({
                    "check": "protected_field_fingerprint",
                    "status": "FAIL",
                    "detail": f"Protected field '{fid}' ({b_fld.get('field_type')}) fingerprint altered. Base: {b_fld.get('fingerprint_sha256')}, Proposal: {p_fld.get('fingerprint_sha256')}"
                })
            else:
                checks.append({
                    "check": "protected_field_fingerprint",
                    "status": "PASS",
                    "detail": f"Protected field '{fid}' ({b_fld.get('field_type')}) fingerprint intact."
                })

        status = VerificationStatus.PASS if all_passed else VerificationStatus.FAIL
        if not checks:
            checks.append({
                "check": "protected_fields",
                "status": "PASS",
                "detail": "No protected fields present in base document."
            })

        return VerificationLevelResult(status=status, checks=checks)
