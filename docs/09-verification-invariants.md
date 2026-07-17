# Verification and Invariants

## 1. Verification levels

### L1 Package

- ZIP readable;
- required parts and relationships exist;
- no duplicate normalized entries;
- no accidental missing parts;
- untouched parts match original hashes.

### L2 XML

- all changed XML well-formed;
- hardened reparse succeeds;
- expected namespaces/elements exist.

### L3 Open XML schema

Run `.NET OpenXmlValidator` and collect errors with part/path. New errors are blocking. Existing errors may be baseline-tagged but proposal must not increase them unless explicitly repairing.

### L4 Structural invariants

- target anchors resolved as intended;
- protected intervals outside operations unchanged;
- field stacks balanced;
- bookmarks/comments/reference ranges remain valid;
- relationship targets remain available;
- table cells remain schema-valid.

### L5 Citation invariants

For untouched fields:

- exact concatenated instruction string hash unchanged;
- canonical subtree hash unchanged;
- result text hash unchanged;
- boundary/nesting signature unchanged;
- relative paragraph anchor unchanged unless operation explicitly moved container.

For inserted/edited fields, adapter-specific verification must pass.

### L6 Semantic diff

- text modifications match plan exactly;
- no unexpected paragraph changes;
- source/evidence report complete;
- unsupported claims reported;
- style/format changes bounded.

### L7 Application round trip

CI/manual fixture tier may open/save using Microsoft Word/Mendeley where licensing/environment permits. Native adapter release requires this tier.

## 2. Fingerprints

Use SHA-256. Canonical XML hash uses stable canonicalization selected and documented by implementation. Also retain raw bytes of relevant subtree when extractable for diagnostics, but canonical fingerprints are normative.

## 3. Before/after manifest

Every proposal stores:

```json
{
  "base_package_hash": "...",
  "proposal_package_hash": "...",
  "changed_parts": ["/word/document.xml"],
  "operation_results": [],
  "invariant_results": [],
  "validator_errors_before": [],
  "validator_errors_after": []
}
```

## 4. Failure handling

- Mark proposal `VERIFICATION_FAILED`.
- Retain base version.
- Do not emit final download.
- Return user-safe explanation and developer diagnostic code.
- Never ask LLM to “repair XML” directly.

## 5. Optional AI semantic verifier

AI verifier receives instruction, limited before/after text, plan, and evidence IDs—not XML. It checks intent, coherence, citation-context fit, repetition, and academic tone. Its output is advisory unless configured blocking for specific policies.
