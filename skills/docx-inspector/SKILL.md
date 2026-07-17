# Skill: DOCX Inspector

Use when implementing or reviewing upload validation, OPC inventory, WordprocessingML parsing, text projection, stable anchors, fields, and editability classification.

## Procedure

1. Read `docs/03-docx-domain-model.md` and `docs/04-docx-inspection-parsing.md`.
2. Add/extend a fixture before parser behavior.
3. Parse package relationships rather than fixed paths only.
4. Use hardened XML parser and field stack.
5. Persist logical graph identifiers, not lxml node objects.
6. Produce no mutations.
7. Add golden graph and protected-feature tests.

## Safety boundary

This skill never authorizes an AI model to directly mutate XML. Follow `AGENTS.md`, schemas, and non-negotiable requirements. Fail closed and preserve original files.

