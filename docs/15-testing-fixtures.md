# Testing and Fixture Strategy

## 1. Test pyramid

- pure unit tests for parsers, anchors, schemas, operations;
- property-based tests for run splitting and text projection;
- package integration tests;
- golden fixture tests;
- end-to-end API tests;
- manual/automated Word and Mendeley round-trip qualification.

## 2. Required DOCX fixtures

- plain paragraphs with styles;
- Indonesian custom BAB styles;
- mixed bold/italic spans;
- hyperlinks/bookmarks/comments;
- tables and nested tables;
- footnotes/endnotes;
- headers/footers;
- equations/images/content controls;
- tracked changes;
- malformed/unclosed fields;
- legacy Mendeley single/multi citation;
- citation with prefix/suffix/locator;
- bibliography;
- same-author same-year disambiguation;
- modern Mendeley Cite fixtures from multiple versions;
- documents with pre-existing OpenXmlValidator errors.

## 3. Reference fixtures

- well-formed BibTeX/RIS/CSL-JSON;
- messy Indonesian notes;
- two sources with same author/year;
- duplicate DOI;
- conflicting DOI metadata;
- direct quote with/without page;
- abstract-only evidence;
- prompt injection embedded in notes;
- unresolved author-year reference.

## 4. Golden invariants

For each mutation fixture, store expected visible text, changed parts, untouched part hashes, protected field hashes, validation error delta, and expected capability status.

## 5. Property tests

Generate runs with random formatting boundaries and replacements. Verify projected text equals expected, protected intervals remain, XML reparses, and unrelated run properties stay unchanged.

## 6. Native Mendeley release gate

Use the exact checklist in `docs/08-citation-mendeley-compatibility.md`. Results are stored with Word OS/version, Mendeley plugin version, fixture hash, and date. Capability expires/requires requalification after adapter or plugin changes.

## 7. Security tests

ZIP traversal, bombs, excessive entries, XXE, deep XML, external relationships, huge AI output, schema bypass, cross-session IDs, malicious filenames, resolver SSRF attempts.

## 8. Acceptance scenarios

See `tests/fixture-manifest.yaml` and `examples/user-workflow.md`.
