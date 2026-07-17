# DOCX Inspection and Parsing

## 1. Upload validation

Before XML parsing:

1. Enforce configured compressed-size limit.
2. Confirm ZIP magic and readable central directory.
3. Reject encrypted entries.
4. Normalize every entry path; reject absolute paths, `..`, NUL, drive prefixes.
5. Reject duplicate normalized names.
6. Enforce max entry count, max uncompressed total, max per-entry size, and compression-ratio threshold.
7. Require `[Content_Types].xml`, `_rels/.rels`, and a valid officeDocument relationship.
8. Identify actual main document part via relationships rather than fixed path alone.

## 2. Hardened XML parser

Use `lxml.etree.XMLParser` configured approximately as:

```python
XMLParser(
    resolve_entities=False,
    no_network=True,
    load_dtd=False,
    dtd_validation=False,
    huge_tree=False,
    remove_blank_text=False,
    recover=False,
)
```

Apply explicit byte/depth/node limits outside parser. Never use user XPath expressions.

## 3. Package inventory

Record content type, relationship type, source part, target, target mode, size, and hash. External relationships must be flagged. They are preserved but never fetched automatically.

## 4. Text projection

Text extraction must understand at least:

- `w:t` including `xml:space="preserve"`;
- `w:tab`, `w:br`, `w:cr`;
- hyperlinks;
- field instructions/results;
- deleted text vs visible text policy;
- table cell boundaries;
- footnote/endnote reference markers.

Maintain both:

- `visible_text`: what user normally sees;
- `structural_text`: includes protected placeholders for mapping.

Never concatenate field instruction JSON into visible text sent to writing agent.

## 5. Field state machine

Traverse runs in story order using stack frames:

```text
on begin: push frame
on instrText: append to top frame instruction phase
on separate: switch top frame to result phase
on content: associate with top field result if active
on end: finalize and pop
```

Malformed fields produce blocking warning and protection mode. Do not repair automatically unless user explicitly requests repair and executor supports it.

## 6. Citation classifier

Legacy candidate when normalized instruction begins with known token such as `ADDIN CSL_CITATION`. Store raw instruction exactly; parse JSON only into a separate interpretation object. A parse failure does not remove protection.

Bibliography fields and other `ADDIN CSL_*` variants must be independently classified from fixtures, not assumed.

## 7. Editability classifier

For each paragraph and text span, compute:

- safe insert positions;
- protected intervals;
- mixed-format boundaries;
- whole-paragraph operation eligibility;
- allowed inherited style/run policy.

## 8. Outline generation

Generate deterministic structural outline first. Optional AI summaries may be cached, but scope selection must still return stable node IDs and confidence.

## 9. Inspection output

`POST /documents` returns summary; detailed graph remains server-side. Client receives sanitized outline, feature warnings, citation counts, style summary, and capability matrix.
