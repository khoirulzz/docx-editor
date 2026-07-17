# Security, Privacy, and Threat Model

## 1. Assets

- unpublished academic documents;
- personal data inside documents;
- reference PDFs/notes;
- provider API keys;
- Mendeley OAuth tokens;
- generated files and session metadata.

## 2. Trust boundaries

Browser, backend, uploaded archive/XML, LLM provider, metadata resolvers, object storage, and optional validator are separate boundaries. All external input/output is untrusted.

## 3. Principal threats and mitigations

### Malicious DOCX / ZIP

Mitigate traversal, zip bomb, huge entries, duplicate names, symlink-like patterns, encrypted archives, excessive XML depth, and external entity/network resolution.

### Prompt injection in document/reference text

Document text is data, not instructions. Runtime prompts clearly delimit untrusted content. Planner has no direct tools or secrets. Never follow instructions embedded in uploaded documents.

### AI output injection

Strict JSON schema, enum operations, no XML/path/code fields, length limits, and semantic policy checks.

### Cross-session access

Authenticated ownership checks, cryptographic IDs, signed download URLs, no sequential identifiers, per-session authorization.

### Data leakage through logs

Structured logs contain IDs, sizes, hashes, timings, error codes—not document text, prompts, extracted evidence, tokens, or secrets.

### External resolver abuse

Allowlisted HTTPS domains, timeout, response-size limits, rate limiting, user agent/contact, cache, and no arbitrary URL fetch from AI output.

### OAuth compromise

Authorization Code flow, server-side secret storage, state/PKCE where supported, encrypted token storage, narrow access, revocation, no tokens in logs/query strings.

## 4. Privacy defaults

- Use private/protected deployment appropriate to data sensitivity.
- Provider calls use minimal slices.
- Enable Blackbox ZDR routing where available/configured.
- Default file/session TTL; deletion is verifiable.
- Provide “delete session now”.
- Do not train local models on user files without explicit consent.

## 5. Recommended limits

Configuration, not hardcoded requirement:

- max upload per file;
- max total session upload;
- max archive entries;
- max uncompressed size;
- max compression ratio;
- max XML bytes/nodes/depth;
- max pages/chars indexed;
- max provider request tokens;
- rate limits per user/IP/session.

## 6. Content handling policy

PDF/full text may be processed only when user supplies it or the application is authorized to access it. Store provenance/licensing notes. Export only user-owned/provided content and derived metadata as allowed.

## 7. Security tests

Include malicious archive fixtures, XXE/entity samples, prompt injection text, cross-session authorization tests, oversized plan output, path injection, malformed fields, and secret scanning.
