# System Architecture

## 1. Logical architecture

```text
Browser SPA
  ├─ upload/chat/preview/version UI
  └─ never receives provider secrets
          │ HTTPS
          ▼
FastAPI Application
  ├─ Upload Gateway
  ├─ DOCX Inspector
  ├─ Reference Intake Pipeline
  ├─ Session & Version Store
  ├─ Agent Orchestrator
  ├─ Plan Gateway
  ├─ Deterministic Executor
  ├─ Verification Pipeline
  ├─ Preview/Diff Service
  └─ Export Service
          │
          ├─ Blackbox AI API (backend only, ZDR routing preferred)
          ├─ Crossref/other metadata resolvers
          ├─ CSL processor
          └─ Optional .NET OpenXmlValidator sidecar
```

## 2. Components

### Upload Gateway

Validates extension, MIME hints, ZIP signature, package inventory, size limits, entry count, compression ratio, and required DOCX parts. Stores immutable original by SHA-256.

### DOCX Inspector

Produces a `DocumentGraph` without mutating source. It parses paragraphs/runs/fields/tables/styles/numbering/relationships and derives editability flags.

### Reference Intake Pipeline

Accepts loose notes and structured bibliographic formats. Produces normalized references, evidence units, provenance, confidence, duplicate groups, and retrieval index.

### Session & Version Store

Stores session metadata, immutable package versions, graph snapshots, proposal states, and temporary exports. Node references are logical identifiers, never raw lxml object references in persistent storage.

### Agent Orchestrator

Runs intent/scope selection, evidence retrieval, edit planning, and optional semantic verification. It enforces token budgets and model capability registry.

### Plan Gateway

Validates schema, version, target anchors, scope, protected features, evidence/reference IDs, operation conflicts, and limits.

### Deterministic Executor

Applies approved typed operations. It owns XML construction and style/run policies. It never accepts arbitrary XML or XPath from LLM.

### Verification Pipeline

Performs package, XML, schema, relationship, protected-node, citation, semantic, and optional application round-trip checks.

### Preview Service

Creates textual and structural diff, citation report, warnings, and operation dependency groups. Proposal XML is not committed yet.

## 3. Core state machine

```text
UPLOADING
  → INSPECTING
  → READY
  → PLANNING
  → PLAN_REJECTED | PROPOSAL_READY
  → VERIFYING
  → VERIFICATION_FAILED | AWAITING_APPROVAL
  → COMMITTED | REJECTED
  → EXPORTED
```

Every transition is server-authoritative and idempotency-aware.

## 4. Data flow: edit request

1. Resolve session and committed document version.
2. Classify user intent and target scope.
3. Build outline context if scope ambiguous.
4. Retrieve relevant document slice and evidence slice.
5. Call planner with strict contract.
6. Validate plan.
7. Clone committed package to proposal workspace.
8. Apply operations deterministically in dependency order.
9. Run verification.
10. Build preview and citation report.
11. Await explicit approval.
12. Atomically commit proposal as next version.

## 5. Deployment topology

Initial deployment may run all Python services in one Docker Space. The Open XML validator may be:

- a .NET CLI invoked as a subprocess in the same container; or
- a sidecar in non-HF deployment.

Storage abstraction must support local ephemeral storage for development and object storage for durable/private deployment.
