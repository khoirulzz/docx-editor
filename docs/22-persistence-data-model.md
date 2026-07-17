# Persistence Data Model

The implementation may use SQLite/PostgreSQL plus object storage. The logical model below is normative.

## 1. Tables/entities

### `sessions`

- `session_id` UUID/random public ID;
- `owner_id`;
- `state`;
- `document_id`;
- `head_version`;
- `created_at`, `expires_at`, `deleted_at`;
- privacy/config JSON;
- optimistic lock revision.

### `document_versions`

- session/document/version composite key;
- package blob key and SHA-256;
- graph blob key and SHA-256;
- parent version;
- commit type (`initial`, `edit`, `revert`);
- created_at;
- verification report key.

Immutable after insertion.

### `assets`

- asset ID/session;
- original sanitized display name;
- media type/classification;
- blob key/hash/size;
- intake status;
- TTL.

### `references`

- reference ID/session;
- normalized CSL JSON;
- citation-ready flag;
- identity/metadata status and confidence;
- created/updated timestamps.

### `reference_aliases`

BibTeX keys, source-local IDs, DOI forms, Mendeley IDs.

### `evidence_units`

- evidence ID/reference ID nullable;
- raw/normalized text stored in protected blob or encrypted column;
- classification/locator/topics;
- provenance;
- verification state.

### `proposals`

- proposal ID/session/base version;
- state;
- instruction hash and protected instruction content;
- plan blob/hash;
- result package/graph keys;
- verification key;
- created/expired timestamps.

### `proposal_operations`

- operation ID/type/group/dependencies;
- decision state;
- compact diff/report;
- no raw XML.

### `audit_events`

Minimal event metadata. No document body/prompt content by default.

## 2. Blob storage layout

```text
sessions/<session-id>/original/<sha>.docx
sessions/<session-id>/versions/<n>/<sha>.docx
sessions/<session-id>/graphs/<n>/<sha>.json
sessions/<session-id>/assets/<asset-id>/<sha>
sessions/<session-id>/proposals/<proposal-id>/...
sessions/<session-id>/exports/<export-id>/...
```

Do not trust path fragments from user filenames.

## 3. Transaction rules

- Creating a session and initial version is one logical transaction.
- Committing a proposal checks head version and publishes metadata atomically after blob upload succeeds.
- Failed blob write cannot advance head.
- Deletion marks then asynchronously removes all blobs; status exposes completion.

## 4. Encryption

Use platform/object-store encryption at rest. OAuth refresh tokens require stronger application-level encryption/key management. Hashes are integrity metadata, not encryption.

## 5. Ephemeral deployment

For local/HF ephemeral mode, the same interfaces use filesystem + SQLite. State loss after restart is expected and surfaced as expired/unavailable. Do not promise persistent histories in this mode.
