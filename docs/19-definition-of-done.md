# Definition of Done

## Product DoD

A user can upload a DOCX and messy reference notes, ask to improve Bab II, receive a coherent evidence-linked proposal in APA style, review every change, commit it, and download a valid DOCX without damage to unrelated structure or existing citations.

## Engineering DoD

- all non-negotiable requirements have mapped tests;
- JSON Schemas and OpenAPI pass validation;
- type/lint/unit/integration/security tests pass;
- no high-severity secret/dependency findings;
- no unexpected changed package parts;
- OpenXmlValidator error delta is acceptable;
- protected citation invariants pass;
- proposal/commit/version conflict behavior tested;
- error paths preserve original.

## Reference/citation DoD

- every used source has provenance;
- every new attributable claim links to evidence or is marked unsupported;
- unresolved metadata cannot become final citation;
- CSL style rendering is deterministic/pinned;
- UI correctly labels managed vs non-managed status;
- native Mendeley capability only enabled with documented qualification record.

## Documentation DoD

- README/setup/deployment updated;
- environment variables documented;
- API examples work;
- capability matrix published;
- known limitations and migration notes visible.
