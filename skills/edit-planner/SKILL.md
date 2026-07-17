# Skill: Edit Planner

Use when implementing prompts, context slicing, Blackbox calls, JSON validation, and Plan Gateway.

## Procedure

1. Read `docs/05-edit-plan-protocol.md`, `docs/14-llm-orchestration.md`, and schema.
2. Limit context to allowed scope/evidence.
3. Use provider capability registry.
4. Validate syntax, schema, semantics, policy, and preconditions.
5. Never execute invalid/partial output.
6. Retry only under bounded policy.
7. Test prompt injection and unknown operations.

## Safety boundary

This skill never authorizes an AI model to directly mutate XML. Follow `AGENTS.md`, schemas, and non-negotiable requirements. Fail closed and preserve original files.

