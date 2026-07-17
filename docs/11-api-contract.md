# API Contract Narrative

Machine contract: `api/openapi.yaml`.

## Resource model

- `DocumentSession`: uploaded document and reference workspace.
- `DocumentVersion`: immutable committed version.
- `ReferenceAsset`: uploaded supporting file.
- `ReferenceStore`: normalized references/evidence.
- `Proposal`: plan + execution + verification + diff.
- `Export`: temporary downloadable artifact.

## Key endpoints

- `POST /v1/sessions`: upload DOCX and optional reference assets.
- `GET /v1/sessions/{id}`: summary/capabilities/status.
- `POST /v1/sessions/{id}/assets`: add reference files.
- `POST /v1/sessions/{id}/references/process`: run/re-run intake.
- `GET /v1/sessions/{id}/references/summary`.
- `POST /v1/sessions/{id}/proposals`: natural-language edit request.
- `GET /v1/sessions/{id}/proposals/{proposal_id}`.
- `POST /v1/sessions/{id}/proposals/{proposal_id}/decisions`: accept/reject operations.
- `POST /v1/sessions/{id}/proposals/{proposal_id}/commit`.
- `POST /v1/sessions/{id}/versions/{version}/export`.
- `DELETE /v1/sessions/{id}`.

## Idempotency and concurrency

Mutating POST endpoints accept `Idempotency-Key`. Proposal creation includes `base_version`; commit fails with `409 VERSION_CONFLICT` if committed version has advanced.

## Error envelope

```json
{
  "error": {
    "code": "PRECONDITION_FAILED",
    "message": "Target paragraph changed after planning.",
    "details": {},
    "request_id": "req_..."
  }
}
```

Never include raw document content in server error details.

## Upload behavior

Multipart supports one primary DOCX and multiple assets. Processing may be synchronous for small inputs or return job status. An HF Space implementation can initially use polling endpoints.

## Proposal response

Includes plan summary, operation-level diff, citation/source report, warnings, verification status, and capability mode. Raw internal XML and sensitive graph locators are not returned.

## Downloads

Exports use short-lived authorization-bound URLs or authenticated streaming. Use safe `Content-Disposition` filenames and `application/vnd.openxmlformats-officedocument.wordprocessingml.document`.
