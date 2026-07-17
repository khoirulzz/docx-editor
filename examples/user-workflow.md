# End-to-End Example

## User input

Files:

- `skripsi.docx`
- `catatan-sumber.md`
- optional `library.bib`

Prompt:

> Bantu perbaiki Bab II. Perkaya pembahasan menggunakan sitasi yang relevan dari file pendukung. Gunakan APA 7, prioritaskan parafrasa, jangan mengarang sumber, dan pertahankan sitasi Mendeley yang sudah ada.

## System behavior

1. Validate and inspect DOCX.
2. Detect Bab II and protected citations.
3. Parse loose notes and BibTeX.
4. Resolve/flag metadata.
5. Retrieve evidence relevant to each subsection.
6. Planner creates evidence-linked operations.
7. Plan Gateway rejects unsupported/unsafe operations.
8. Executor creates proposal.
9. Verification checks package, XML, fields, citations, and diff.
10. UI shows:
   - 8 paragraph changes;
   - 6 references used;
   - 2 unresolved notes not used;
   - citation mode label;
   - before/after and warnings.
11. User approves.
12. New version is committed and exported.

## Expected safe behavior

- Prompt injection text inside notes is ignored.
- Existing Mendeley fields remain untouched.
- Yusuf 2024 is not cited because identity is unresolved.
- If native adapter is unavailable, new citations are APA formatted or placeholders with a manifest; UI does not claim they are managed Mendeley.
