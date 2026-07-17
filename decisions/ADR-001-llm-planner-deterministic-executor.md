# ADR-001: LLM Planner, Deterministic Executor

Status: Accepted.

Decision: LLM returns typed JSON plans only; deterministic code owns all DOCX/XML mutation.

Rationale: XML/package integrity, auditability, schema validation, repeatability, least privilege, and protection against prompt/output injection.

Consequences: More executor code and schemas are required; unsupported operations must be rejected rather than improvised.
