# ADR-004: Capability-Gated Native Mendeley Integration

Status: Accepted.

Decision: Preserve existing citations in production. Native insertion/editing is enabled per producer/version only after Word/Mendeley round-trip qualification. Safe fallback is always available.

Rationale: public documentation does not provide a stable universal contract for inserting managed Mendeley Cite objects into arbitrary DOCX.
