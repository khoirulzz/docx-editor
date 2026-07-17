# Skill: Reference Intake

Use when implementing parsers, metadata normalization/resolution, evidence extraction, dedupe, and retrieval.

## Procedure

1. Read `docs/07-reference-intake-evidence.md`.
2. Accept messy user input; never require internal IDs from user.
3. Preserve raw provenance.
4. Never fabricate missing fields.
5. Resolver output records source/confidence/conflicts.
6. Citation-ready requires policy status, not merely parser success.
7. Test Indonesian loose notes and ambiguous author-year cases.

## Safety boundary

This skill never authorizes an AI model to directly mutate XML. Follow `AGENTS.md`, schemas, and non-negotiable requirements. Fail closed and preserve original files.

