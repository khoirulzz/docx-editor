# Deterministic DOCX Executor

## 1. Executor contract

Input: validated `EditPlan`, immutable base package, base `DocumentGraph`, reference store, selected citation/style mode.  
Output: proposal package, new graph, execution report.  
No network and no LLM calls occur inside executor.

## 2. General algorithm

1. Verify package hash and version.
2. Copy base package into isolated proposal workspace.
3. Resolve all target anchors and preconditions.
4. Topologically sort operation dependencies.
5. Apply operations using typed handlers.
6. Update only required XML parts/relationships.
7. Rebuild graph from proposal; never patch graph by assumption only.
8. Produce operation result mapping.
9. Hand proposal to verification pipeline.

## 3. Span replacement

- Validate projected text and exact expected substring.
- Reject if interval crosses protected segments.
- Split start/end runs while preserving run properties.
- Delete covered text nodes only.
- Insert replacement using `inherit_from_start`, `inherit_from_end`, or explicit safe style token.
- Preserve leading/trailing spaces with `xml:space="preserve"` when needed.
- Coalesce adjacent equivalent runs only when configured; default is no aggressive normalization.

## 4. Paragraph insertion

Clone only safe paragraph properties from anchor based on policy:

- `inherit_paragraph_style`;
- `same_list_level` only when requested and numbering is understood;
- `normal_body` resolved from document styles;
- explicit existing style ID.

Do not clone section properties, bookmarks, proofing artifacts, fields, or revision IDs. Generate unique `w14:paraId` when document uses them and the target Office version supports it.

## 5. Paragraph deletion

Before deletion verify:

- no section properties;
- no protected features;
- table cell will retain a valid paragraph;
- no relationship becomes orphaned;
- no chapter boundary deletion unless explicitly requested.

## 6. Table edits

Text edits inside table cells use the same span model. Structural row/column merge/split is out of MVP unless separate executor and tests exist.

## 7. Style handling

Style references use style IDs from `styles.xml`. Display names are not identifiers. Resolve inheritance for preview. Do not recreate or rename styles casually.

## 8. Citation insertion adapter interface

```python
class CitationAdapter(Protocol):
    mode: str
    def supports(self, document_capabilities, references) -> SupportResult: ...
    def insert(self, context, citation_request) -> CitationMutationResult: ...
    def verify(self, before, after, request) -> CitationVerification: ...
```

Adapters:

- `FormattedCslAdapter`
- `PlaceholderManifestAdapter`
- `LegacyMendeleyFieldAdapter`
- `ModernMendeleyCiteAdapter` (disabled until fixture-qualified)

## 9. Bibliography handling

- Formatted CSL mode can create/update a system-owned bibliography block with a content-control/tag marker.
- Never overwrite an existing managed bibliography unless selected adapter can safely own it.
- Native adapters must coordinate citation cluster and bibliography behavior from observed fixtures.

## 10. Repackaging

- Preserve every untouched ZIP entry byte-for-byte when possible.
- Replace only changed part entries.
- Maintain content types and relationships.
- Use safe ZIP compression.
- Final filename contains sanitized original stem and version suffix.
