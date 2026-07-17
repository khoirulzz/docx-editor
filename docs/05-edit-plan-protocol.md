# Edit Plan Protocol

Machine source of truth: `schemas/edit-plan.schema.json`.

## 1. Design principles

- Versioned protocol.
- No XML, XPath, file paths, or arbitrary code.
- Every write has preconditions.
- All citation uses reference/evidence IDs.
- Scope is explicit.
- Operations are small, typed, reviewable, and dependency-aware.

## 2. Plan envelope

Required fields:

- `schema_version`.
- `document_id` and `document_version`.
- `instruction_summary`.
- `scope.allowed_node_ids` or allowed chapter IDs.
- `operations`.
- `used_reference_ids`, `used_evidence_ids`.
- `unsupported_claims`, `warnings`, `assumptions`.

## 3. Supported core operations

### `insert_paragraph_before` / `insert_paragraph_after`

Creates a new paragraph adjacent to target. Requires `paragraph_style_policy` and content blocks.

### `replace_text_span`

Preferred rewrite operation. Requires start/end offsets and exact `expected_text`. Executor splits runs and inherits formatting according to policy.

### `replace_plain_paragraph`

Only for paragraphs classified `whole_replace_safe=true`.

### `delete_plain_paragraph`

Only if safe, not sole required cell paragraph, and not carrying bookmarks/fields/section properties.

### `set_paragraph_style`

Only style ID from document allowlist or configured template; not arbitrary style creation in MVP.

### `insert_citation`

Content-level operation referencing existing normalized IDs. It does not contain author/title invented by AI.

### `remove_citation` / `edit_citation`

Requires exact target citation field ID and capability/policy. Existing managed citation changes need user explicit instruction.

## 4. Content blocks

Inserted paragraph content is ordered blocks:

```json
[
  {"type":"text","text":"..."},
  {
    "type":"citation",
    "reference_ids":["REF-001"],
    "evidence_ids":["EV-001"],
    "citation_mode":"parenthetical",
    "locator":{"label":"page","value":"17"}
  }
]
```

Backend renders citation display with CSL and chooses insertion adapter.

## 5. Operation dependencies

Operations have `operation_id`, optional `depends_on`, and `group_id`. A citation inserted into a new paragraph depends on paragraph creation. Partial acceptance must respect dependency closure.

## 6. Limits

Configurable hard limits:

- max operations/plan;
- max inserted characters;
- max deleted characters;
- max affected chapters;
- max new citations;
- max direct quotes;
- max fraction of target section rewritten.

Exceeding a limit returns a planning warning or requires split proposals.

## 7. Semantic validation

Validate:

- target exists and belongs to version/scope;
- operation allowed by editability classification;
- span does not overlap protected intervals;
- expected hashes/text match;
- reference and evidence relationships are valid;
- evidence supports intended claim at policy level;
- no duplicate/overlapping operations;
- ordering remains deterministic;
- explicit user intent exists for citation deletion/edit.

## 8. Execution ordering

Resolve all anchors against original proposal base first. Execute descending offsets within one paragraph, then structural operations using stable node references. Never let earlier insertion silently retarget later ordinal-based operations.
