# Skill: DOCX Executor Review

Use before adding or changing any mutation handler.

## Review checklist

- Typed operation only; no arbitrary XML/XPath.
- Anchor/version/hash preconditions.
- Protected interval checks.
- Run splitting preserves formatting and whitespace.
- Only expected parts changed.
- Graph rebuilt after mutation.
- Proposal isolated from base.
- Unit, property, integration, and golden tests.
- Citation adapter capability gate honored.

## Safety boundary

This skill never authorizes an AI model to directly mutate XML. Follow `AGENTS.md`, schemas, and non-negotiable requirements. Fail closed and preserve original files.

