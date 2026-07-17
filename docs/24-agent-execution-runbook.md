# Coding Agent Execution Runbook

## Phase 1: Understand

1. Read `README.md`, `AGENTS.md`, and accepted ADRs.
2. Validate JSON Schema/OpenAPI files.
3. Create requirement IDs for every MUST in `docs/01-*`.
4. Map requirement IDs to modules and tests.
5. Report any direct contradictions; absence of detail is not permission to violate principles.

## Phase 2: Scaffold

1. Create repository tree recommended by `AGENTS.md`.
2. Pin Python and frontend dependencies.
3. Add lint/type/test/security CI.
4. Add config model using `.env.example`.
5. Add empty capability registry with native adapters disabled.

## Phase 3: Implement by vertical slice

For each milestone:

1. Add fixture/test first.
2. Implement pure domain code.
3. Integrate API.
4. Add UI only after contract works.
5. Run regression and changed-part inspection.
6. Update docs/ADR/capability matrix.
7. Commit a milestone report.

## Phase 4: Review gates

Before merging a mutation handler:

- use `skills/docx-executor-review/SKILL.md`;
- confirm no arbitrary XML pathway;
- test stale versions and protected overlaps;
- run package/field fingerprints.

Before enabling native citation:

- use `docs/23-native-mendeley-rnd-protocol.md`;
- attach qualification record;
- keep fallback UI available.

## Phase 5: Release

1. Run full fixture/security suite.
2. Validate OpenAPI against running server.
3. Verify secrets and log redaction.
4. Test file TTL/deletion and restart behavior.
5. Publish supported capability matrix and known limitations.
6. Do not advertise unsupported native Mendeley behavior.
