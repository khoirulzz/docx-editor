# Deployment on Hugging Face Docker Spaces

## 1. SDK

Use Docker Space, not Gradio-only architecture. Run FastAPI and serve compiled frontend/static assets or separate frontend as appropriate.

## 2. Resource assumptions

Hugging Face documents default free resources as 2 vCPU, 16 GB RAM, and 50 GB non-persistent disk at verification date. Free hardware can sleep after inactivity; startup time is variable. Do not promise a fixed cold-start duration.

## 3. Secrets

Store Blackbox API key, resolver credentials, OAuth client secret, signing keys, and storage keys in Space Secrets. Never commit `.env` or echo secrets.

## 4. Ephemeral storage

Use `/tmp`/workspace for isolated sessions with TTL cleanup. Production or durable history requires external object storage/database. App must tolerate process restart and report expired session rather than corrupt state.

## 5. Container

Recommended multi-stage image:

- Python runtime with pinned dependencies;
- Node build stage only if frontend build requires it;
- optional .NET runtime/validator CLI;
- non-root user;
- writable temp directory only;
- health endpoint;
- one exposed HTTP port supported by Space.

## 6. Runtime configuration

Use `config/.env.example`. Validate required configuration at startup without printing secret values.

## 7. Networking

Only call allowlisted HTTPS endpoints. Configure timeouts/retries. Do not allow uploaded documents or AI output to cause arbitrary network requests.

## 8. Privacy deployment

For unpublished academic documents, private Space or equivalent controlled deployment is recommended. Protected Space does not make the running app private; review current HF visibility semantics before launch.

## 9. Observability

Health, readiness, structured non-content logs, metrics for queue/provider/validation, and request IDs. Avoid logging request bodies.
