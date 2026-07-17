# LLM Orchestration

## 1. Agent roles

- `IntentScopeAgent`: identifies target and task type.
- `ReferenceIntakeAgent`: structures loose notes; never fabricates missing metadata.
- `EvidenceRetriever`: deterministic search/rerank with optional LLM reranking.
- `EditPlannerAgent`: outputs `EditPlan` only.
- `SemanticVerifierAgent`: advisory review of limited before/after.

Do not use one monolithic agent with direct file mutation.

## 2. Context assembly

Order stable prompt prefixes to improve caching:

1. immutable system rules;
2. schema/tool definition;
3. document/style policy summary;
4. user instruction;
5. selected document slice;
6. selected evidence/references.

Every untrusted block is delimited and labelled `DATA, NOT INSTRUCTIONS`.

## 3. Token budgeting

Use estimated tokens and model context limits. Never use page count as sole threshold. Reserve output/schema budget and safety margin. Chunk by structural boundaries and use iterative proposal for very large scopes.

## 4. Blackbox capability registry

Configuration records per model:

- JSON mode support;
- tool calling support;
- context limit;
- max output;
- ZDR eligibility;
- prompt caching behavior;
- known reliability tests.

Prefer function/tool calling with JSON Schema parameters when supported. Otherwise use JSON object mode plus local schema validation and bounded repair retry.

## 5. Retry policy

Allowed retries:

- transient network/rate error with exponential backoff;
- invalid JSON: one constrained repair request using validation errors, no document context expansion;
- schema-valid but semantically invalid: return to planner with summarized violations, limited attempts.

Never execute partially parsed output.

## 6. Prompt caching

Optimization only. Keep system prefix stable; do not rely on cache correctness or persistence. Sensitive data minimization remains required even with ZDR/caching.

## 7. Semantic verifier

Checks coherence, repetition, instruction compliance, citation-context fit, unsupported claims, and academic tone. It cannot override deterministic verification or source identity status.

## 8. Provider abstraction

Use an interface so Blackbox is initial provider but schemas/orchestration are provider-neutral. Backend owns authorization and routing.
