# DOCX Domain Model

## 1. Package model

A `.docx` is an OPC ZIP package. The application must inventory rather than assume only these parts:

- `[Content_Types].xml`
- `_rels/.rels`
- `word/document.xml`
- `word/_rels/document.xml.rels`
- `word/styles.xml`
- `word/numbering.xml`
- headers/footers
- footnotes/endnotes/comments
- settings/theme/fontTable
- media/embeddings/customXml

Unknown parts are preserved unchanged unless a typed operation explicitly targets them.

## 2. Stories

A field must start and end within a document story. Supported story identifiers:

- `main`
- `header:<part>`
- `footer:<part>`
- `footnotes`
- `endnotes`
- `comments`
- optional text-box stories when inspectable

MVP mutation target is main story and safe table cells. Other stories are inspectable/protected until feature-specific executors exist.

## 3. DocumentGraph

Canonical persisted representation:

```json
{
  "document_id": "doc_<uuid>",
  "version": 3,
  "package_sha256": "...",
  "nodes": [],
  "fields": [],
  "chapters": [],
  "relationships": [],
  "capabilities": {}
}
```

### Paragraph node

- `node_id`: stable logical ID.
- `story_id`.
- `ordinal`: display order only.
- `para_id`: `w14:paraId` if present.
- `locator`: deterministic fallback locator.
- `text`, `text_hash`.
- `style_id`, resolved style, outline level.
- `parent_node_id`: body/table-cell/content-control.
- `features`: protected constructs.
- `editability`: allowed operation set.

### Run segment

Text projection is represented by segments mapping character offsets to XML nodes:

```json
{
  "segment_id": "seg_...",
  "start": 0,
  "end": 12,
  "kind": "text|field_code|field_result|tab|break|drawing|reference",
  "run_properties_hash": "...",
  "protected": false
}
```

Offset mapping must treat tabs/breaks with explicit tokens so span edits are deterministic.

## 4. Stable anchors

Target identity precedence:

1. `story_id + w14:paraId` when unique.
2. Generated node ID stored in session graph plus version.
3. Fallback locator: parent chain + neighboring text hashes + style + ordinal window.

Every mutation includes:

- expected document version;
- expected target text hash;
- optional exact expected text span;
- allowed scope IDs.

If anchor resolution is not unique or hash mismatch occurs, reject with `PRECONDITION_FAILED`.

## 5. Fields

Complex fields are sequences:

```text
fldChar(begin) → instruction runs → optional fldChar(separate)
→ result runs → fldChar(end)
```

Fields can be nested. Store:

- `field_id`;
- `story_id`;
- begin/separate/end locators;
- instruction text fragments and concatenated exact value;
- result segment range;
- nesting depth;
- classifier (`mendeley_legacy_citation`, `bibliography`, `toc`, `cross_reference`, `unknown`);
- hashes and protection policy.

## 6. Protected features

A paragraph is whole-replace-ineligible when it contains any of:

- field code/result;
- hyperlink;
- bookmark start/end;
- comment range/reference;
- drawing/object/equation;
- footnote/endnote reference;
- tracked revision (`w:ins`, `w:del`, etc.);
- content control (`w:sdt`);
- mixed formatting that cannot be safely mapped;
- unknown markup.

## 7. Chapter/section model

Chapter detection combines:

- resolved outline level;
- style ID/name;
- numbering properties;
- text patterns (`BAB II`, Roman/Arabic forms);
- formatting heuristics;
- user correction.

Each result has confidence and evidence. Do not hardcode English style names.

## 8. Serialization policy

- Preserve ZIP entry names/order where practical; preserve untouched bytes for non-mutated parts.
- Parse only parts needed for inspection/mutation.
- For mutated XML, preserve namespace declarations and whitespace as much as possible.
- Byte identity for entire XML is not guaranteed after parse/serialize; protected subtree semantic/canonical fingerprints are normative.
