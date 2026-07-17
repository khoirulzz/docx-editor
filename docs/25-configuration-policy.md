# Configuration and Policy

## 1. Configuration categories

- runtime/deployment;
- storage/TTL;
- archive/XML limits;
- provider/model routing;
- privacy/ZDR;
- planning/token limits;
- reference resolution;
- citation style/mode;
- feature capabilities.

Validate all configuration at startup with typed models.

## 2. Policy precedence

1. security and non-negotiable requirements;
2. server/admin policy;
3. document/session policy;
4. explicit user instruction;
5. inferred defaults.

User prompts cannot disable structural verification, secret protection, source provenance, or native capability gates.

## 3. Citation defaults

Recommended:

- style: infer existing style if reliably detected, otherwise configured APA 7/user choice;
- citation mode: `auto`, resolving to native only when qualified; otherwise formatted CSL or placeholder according to user preference;
- preserve existing managed citations: always true;
- bibliography: preview impact before commit;
- unresolved sources: blocking for final citation.

## 4. Editing defaults

- preserve language and academic register;
- prefer paragraph-local span edits;
- prefer paraphrase unless user requests verified direct quote;
- do not rewrite outside selected scope;
- preserve headings/numbering/styles;
- split very large changes into proposals.

## 5. Capability registry example

See `config/capabilities.example.yaml`. Capabilities are evidence-backed runtime data, not marketing constants.
