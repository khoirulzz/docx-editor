# Citation and Mendeley Compatibility

## 1. Separation of concerns

- **Reference metadata**: author, year, title, DOI.
- **Citation rendering**: APA/IEEE/etc., handled by CSL processor.
- **Managed citation object**: Word/Mendeley-specific structure.

A correct APA string is not automatically a managed Mendeley citation.

## 2. Mandatory production baseline

- Detect and protect existing citation fields.
- Preserve untouched field instruction/result/boundaries.
- Render new citations accurately in selected CSL style.
- Provide citation manifest and bibliographic export.
- Clearly label whether new citations are managed, formatted-only, or placeholders.

## 3. Legacy field model

Observed legacy documents may contain complex fields whose instruction begins with `ADDIN CSL_CITATION` followed by JSON. Implement parser as fixture-driven state machine. Do not assume the instruction is one `w:instrText` node or one run.

Store raw instruction and parsed interpretation separately. When editing, modify only permitted JSON paths and preserve unknown properties.

## 4. Modern Mendeley Cite

Mendeley’s public user guides document insertion/editing/style changes through the Word add-in, while the developer API documents library resources and OAuth. The specification package does not assume a public API exists for inserting a managed citation into arbitrary DOCX.

Therefore modern native insertion requires empirical fixture discovery and round-trip qualification.

## 5. Capability matrix

For each detected producer/version, store:

```json
{
  "producer": "mendeley_legacy|mendeley_cite|unknown",
  "preserve": "supported|unsupported",
  "edit_existing": "experimental|supported|unsupported",
  "insert_new": "experimental|supported|unsupported",
  "bibliography_refresh": "manual|supported|unsupported",
  "fixture_suite_version": "..."
}
```

UI only offers supported capabilities.

## 6. Native adapter qualification gate

A native adapter must pass all of these on real fixture documents:

1. Open original in supported Microsoft Word version.
2. Insert known citation with official Mendeley plugin; save fixture.
3. Inspector identifies exact field/metadata/result.
4. Application inserts another citation.
5. Open modified file in Word without repair dialog.
6. Select inserted citation through Mendeley UI.
7. Edit locator/prefix/suffix.
8. Change citation style.
9. Refresh references.
10. Generate/update bibliography.
11. Save, close, reopen.
12. Verify citation remains managed and metadata correct.
13. Validate package with Open XML SDK.
14. Verify pre-existing untouched citations remain fingerprint-identical.

Gate is per producer family and may be per plugin/version.

## 7. Safe fallback modes

### Formatted CSL

Insert citation display text with a system-owned content control/tag, not pretending to be Mendeley managed. Maintain a manifest mapping anchor to references/evidence.

### Placeholder manifest

Insert a visible review placeholder or Word content control containing stable request ID. Export `.bib/.ris` and instructions. User replaces via Mendeley Cite.

## 8. Existing citation editing

Only when user explicitly asks. The plan references `field_id`; executor validates current instruction hash. Preserve unknown JSON keys and field structure. Deleting a citation also triggers bibliography impact analysis.

## 9. APA style

Use a pinned CSL style file/version and citation processor. AI chooses semantic mode (`parenthetical` or `narrative`) and reference IDs; processor owns names, year disambiguation, et al., punctuation, sorting, and bibliography formatting.

## 10. Bibliography ownership

Classify bibliography as:

- existing managed bibliography: protected unless qualified native adapter owns update;
- system-owned CSL bibliography: identifiable by content control/tag;
- plain text bibliography: editable only with explicit scope and warnings.

## 11. Honest product language

Never display “Mendeley citation inserted” unless native adapter gate passed for the document. Use labels:

- `Managed Mendeley`
- `APA formatted, not managed`
- `Requires final insertion in Mendeley`
