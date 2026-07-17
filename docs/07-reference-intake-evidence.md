# Reference Intake and Evidence Pipeline

## 1. UX objective

User may provide unstructured material. Example:

```text
Digitalisasi bukan hanya memindahkan aktivitas ke online tetapi mengubah proses kerja.
(Ulum, 2026, halaman 17)
Sumber: Ulum. Digitalisasi Bukan Hanya Teknologi Online. Jurnal X 1(2).
DOI 10.xxxx/example
```

System—not user—creates normalized IDs, metadata objects, evidence units, and verification states.

## 2. Accepted input classes

- loose `.txt` / `.md`;
- `.bib` BibTeX;
- `.ris`;
- `.csv` with mapping UI;
- CSL-JSON / structured reference pack;
- DOCX notes;
- PDF source documents, processed once into chunks/evidence candidates;
- metadata already embedded in main DOCX citations.

## 3. Pipeline stages

```text
File classifier
→ safe text extraction
→ source/evidence segmentation
→ candidate metadata extraction
→ reference normalization
→ evidence classification
→ metadata resolution
→ deduplication
→ confidence/policy status
→ retrieval indexing
```

## 4. Reference identity

Internal IDs are generated independently of mutable citation keys:

- Prefer canonical DOI identity: `ref:doi:<normalized>`.
- Else stable UUID with source fingerprint.
- Preserve original BibTeX key as alias, not primary identity.

## 5. Evidence unit

Each evidence contains:

- evidence ID;
- reference ID or unresolved candidate group;
- raw user text;
- normalized claim text;
- classification: `direct_quote`, `paraphrase`, `summary`, `abstract_summary`, `note`, `unknown`;
- locator/page/section if known;
- context notes;
- allowed/support topics;
- prohibited overclaims if generated/reviewed;
- provenance file and offsets;
- verification status.

AI classification is a proposal. Quotation marks alone are not proof of exactness. A direct quote used in final output must be source-verified or explicitly accepted with warning.

## 6. Metadata normalization

Canonical internal format follows CSL-JSON concepts. Never overwrite user-supplied raw data. Store:

- normalized value;
- original value;
- source/resolver;
- confidence;
- conflicts.

## 7. Metadata resolution

### DOI path

Normalize DOI; query Crossref polite pool with application contact; compare title/author/year. Exact DOI response can set identity verified while field conflicts remain visible.

### Title path

Search title + first author + year. Score title similarity, author overlap, year distance, container similarity. Do not auto-resolve below threshold or when top candidates are close.

### Insufficient identity

Author-year only remains unresolved. It can inform drafting as user note but cannot produce final academic citation.

## 8. Deduplication

Signals:

1. exact normalized DOI;
2. PMID/ISBN/URL identifiers;
3. normalized title + year + author;
4. fuzzy title and metadata.

Merge only high-confidence duplicates. Preserve aliases and source provenance.

## 9. Retrieval

Build lexical search initially; optional embeddings later. Query combines instruction, target subsection, nearby paragraph, and missing-claim analysis. Return diverse evidence by topic/source/role, not merely highest similarity.

## 10. Evidence-to-claim policy

The planner must link every new externally attributable claim to one or more evidence IDs. The verifier checks:

- evidence belongs to cited source;
- claim does not exceed evidence category;
- direct quote text/locator requirements;
- unresolved references are not cited;
- one source is not overused without reason;
- contradictory evidence can be represented rather than silently ignored.

## 11. User review summary

UI hides schema complexity and shows:

- ready references;
- unresolved/ambiguous references;
- duplicates;
- evidence quality;
- references used/not used and reasons.

## 12. Export

Provide normalized `.bib`, optional RIS/CSL-JSON, and citation manifest for references used in proposal. User can import the library into Mendeley when native insertion is unavailable.
