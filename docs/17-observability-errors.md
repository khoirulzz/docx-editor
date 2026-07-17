# Observability and Error Taxonomy

## 1. Structured event fields

- timestamp;
- request ID/session pseudonymous ID;
- component;
- operation/job type;
- duration;
- input sizes/counts, never content;
- result code;
- provider/model and token counts where permitted;
- verification summary counts.

## 2. Error codes

- `INVALID_DOCX_PACKAGE`
- `ARCHIVE_LIMIT_EXCEEDED`
- `XML_PARSE_FAILED`
- `UNSUPPORTED_DOCUMENT_FEATURE`
- `FIELD_STRUCTURE_MALFORMED`
- `REFERENCE_UNRESOLVED`
- `REFERENCE_AMBIGUOUS`
- `PLAN_JSON_INVALID`
- `PLAN_SCHEMA_INVALID`
- `PLAN_POLICY_VIOLATION`
- `PRECONDITION_FAILED`
- `VERSION_CONFLICT`
- `EXECUTION_FAILED`
- `OPENXML_VALIDATION_FAILED`
- `CITATION_INVARIANT_FAILED`
- `NATIVE_CITATION_UNSUPPORTED`
- `PROVIDER_UNAVAILABLE`
- `SESSION_EXPIRED`
- `ACCESS_DENIED`

## 3. User messages

Messages explain action without internal XML dump. Example:

> Bagian target berubah sejak proposal dibuat. Proposal tidak diterapkan dan dokumen asli tetap aman. Buat ulang proposal dari versi terbaru.

## 4. Diagnostics

Developer diagnostics may store part URI, node logical ID, validation code, and hashes. Do not store raw citation JSON or paragraph text unless secure debug mode is explicitly enabled in a non-production environment.
