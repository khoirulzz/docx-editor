# ADR-002: Stable Anchors Instead of Paragraph Index

Status: Accepted.

Decision: Use versioned node IDs, `w14:paraId` when available, fallback locators, and expected hashes. Ordinal indices are display-only.

Rationale: insert/delete shifts indices; stale plans otherwise edit the wrong paragraph.
