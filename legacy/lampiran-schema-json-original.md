# Lampiran Teknis: Schema & Contoh JSON
(Pelengkap `blueprint-ai-docx-editor.md` — dokumen ini berisi detail struktur data konkret yang dirujuk di blueprint)

## 1. Struktur `paragraphs` (representasi internal per session)
```json
{
  "index": 42,
  "style": "Normal",
  "text": "Penelitian terdahulu menunjukkan bahwa...",
  "xml_path": "w:body/w:p[43]"
}
```
- `style`: "Normal" | "Heading 1" | "Heading 2" | dst — diambil dari `w:pStyle` di XML
- `xml_path`: referensi posisi node asli, dipakai backend saat eksekusi edit (bukan dikirim ke AI)

## 2. Struktur `chapters`
```json
{
  "title": "BAB III METODE PENELITIAN",
  "start_index": 40,
  "end_index": 78
}
```

## 3. Struktur `citation_fields`
```json
{
  "index": 45,
  "citation_id": "a1b2c3d4",
  "raw_json": {
    "citationID": "a1b2c3d4",
    "properties": { "noteIndex": 0 },
    "citationItems": [
      {
        "id": "12345",
        "itemData": {
          "author": [{ "family": "Sugiyono", "given": "" }],
          "issued": { "date-parts": [[2019]] },
          "title": "Metode Penelitian Kuantitatif"
        }
      }
    ]
  },
  "xml_path": "w:body/w:p[46]/w:r[2]"
}
```
- `raw_json` inilah yang diedit kalau user minta ubah/tambah sitasi
- Field yang index-nya tidak masuk dalam rencana edit AI → `raw_json` dan `xml_path` WAJIB tidak disentuh backend

## 4. Format outline yang dikirim ke AI (tahap outline-first)
Kirim ringkas, bukan isi penuh:
```json
{
  "chapters": [
    { "title": "BAB I PENDAHULUAN", "summary": "Latar belakang, rumusan masalah, tujuan" },
    { "title": "BAB III METODE PENELITIAN", "summary": "Jenis penelitian, populasi/sampel, teknik analisis data" }
  ]
}
```
AI diminta balas cukup:
```json
{ "relevant_chapter": "BAB III METODE PENELITIAN" }
```

## 5. Format request AI plan (backend → Blackbox API)
```json
{
  "instruction": "Tambahkan referensi pendukung untuk teknik analisis data",
  "context_paragraphs": [
    { "index": 55, "text": "Teknik analisis data menggunakan..." },
    { "index": 56, "text": "Uji validitas dilakukan dengan..." }
  ]
}
```

## 6. Format response AI plan (Blackbox → backend) — WAJIB skema ini, bukan XML mentah
```json
{
  "operations": [
    {
      "operation": "insert_after",
      "index": 55,
      "text": "Menurut Sugiyono (2019), teknik analisis data kuantitatif memerlukan uji normalitas sebelum uji hipotesis."
    },
    {
      "operation": "replace_paragraph",
      "index": 56,
      "new_text": "Uji validitas dilakukan dengan teknik korelasi Pearson, sebagaimana dijelaskan oleh Sugiyono (2019)."
    }
  ],
  "citation_operations": [
    {
      "operation": "add_citation",
      "after_index": 55,
      "citation_data": {
        "author": [{ "family": "Sugiyono", "given": "" }],
        "issued": { "date-parts": [[2019]] },
        "title": "Metode Penelitian Kuantitatif"
      }
    }
  ]
}
```
- `operation` yang valid: `insert_after`, `insert_before`, `replace_paragraph`, `delete_paragraph`
- `citation_operations` valid: `add_citation`, `edit_citation`, `remove_citation` — hanya dieksekusi backend, tidak pernah langsung menulis field XML dari teks AI

## 7. API Contract — request/response konkret

### `POST /upload`
Request: multipart form-data, field `file` (.docx)
Response:
```json
{
  "session_id": "sess_8f2a",
  "outline": [
    { "title": "BAB I PENDAHULUAN" },
    { "title": "BAB III METODE PENELITIAN" }
  ]
}
```

### `POST /chat`
Request:
```json
{
  "session_id": "sess_8f2a",
  "message": "Tambahkan referensi di Bab III soal teknik analisis data"
}
```
Response:
```json
{
  "plan": { "operations": [ /* lihat bagian 6 */ ] },
  "diff_preview": [
    { "index": 56, "before": "Uji validitas dilakukan dengan teknik korelasi.", "after": "Uji validitas dilakukan dengan teknik korelasi Pearson, sebagaimana dijelaskan oleh Sugiyono (2019)." }
  ],
  "verification": { "xml_valid": true, "untouched_citations_intact": true }
}
```

### `POST /confirm`
Request:
```json
{ "session_id": "sess_8f2a", "approve": true }
```
Response: binary .docx (atau URL sementara ke file hasil)

### `POST /undo`
Request:
```json
{ "session_id": "sess_8f2a" }
```
Response:
```json
{ "status": "reverted", "current_state_version": 3 }
```

## 8. Skema validasi minimal sebelum eksekusi operasi (pseudocode)
```python
def validate_operation(op, paragraphs):
    assert op["operation"] in ["insert_after", "insert_before", "replace_paragraph", "delete_paragraph"]
    assert any(p["index"] == op["index"] for p in paragraphs)  # index harus ada di dokumen
    return True

def apply_and_verify(original_xml, operations, citation_fields_before):
    new_xml = apply_operations(original_xml, operations)
    assert is_well_formed_xml(new_xml)
    citation_fields_after = extract_citation_fields(new_xml)
    untouched = [c for c in citation_fields_before if c["index"] not in [op.get("after_index") for op in operations]]
    assert all(c in citation_fields_after for c in untouched)  # citation yang tidak disebut tetap identik
    return new_xml
```
