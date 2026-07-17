# Session, Versioning, and Storage

## 1. Immutable object model

- `original_blob`: immutable uploaded package.
- `committed_version`: immutable package and graph snapshot.
- `proposal_version`: mutable only during isolated execution; becomes immutable after verification.
- `export_blob`: derived temporary output.

## 2. Session fields

See `schemas/session.schema.json`. Include owner, state, current version, document hash, TTL, assets, proposals, capability matrix, privacy settings, and audit events.

## 3. Version semantics

Version number increments only on commit. Rejected proposal does not create a committed version. Undo means selecting an earlier committed version as new head or creating a revert commit; never mutate history.

## 4. Concurrency

Optimistic concurrency using `base_version` and package hash. One proposal may run while another exists, but only one can commit against the same head. Stale proposals require replan/rebase.

## 5. Storage backends

Interface supports:

- local ephemeral filesystem for development/HF free tier;
- S3-compatible object storage for production;
- optional database for metadata/events.

No persistent `lxml` node objects. Store graph JSON and resolve against package on load.

## 6. TTL and deletion

Default TTL configurable. Cleanup deletes blobs, graph, provider cache references, exports, and OAuth data association. “Delete now” is idempotent. Audit retains only minimal non-content deletion event when policy permits.

## 7. Content addressing

Use SHA-256 for dedupe/integrity. Hash does not replace authorization. Do not expose content hash as public download key.
