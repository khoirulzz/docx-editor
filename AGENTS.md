# Instructions for the Building Agent

## Mission

Bangun aplikasi sesuai seluruh spesifikasi dalam workspace ini. Jangan mengganti arsitektur inti dengan pendekatan yang memberi LLM akses langsung ke XML atau yang memproses DOCX sebagai teks datar.

## Source of truth precedence

1. `docs/01-non-negotiable-requirements.md`
2. JSON Schemas di `schemas/`
3. `api/openapi.yaml`
4. Dokumen desain lain
5. Contoh
6. `legacy/` — hanya histori; jangan digunakan ketika bertentangan dengan spesifikasi baru.

## Required implementation behavior

1. Buat implementation plan per milestone dari `docs/18-implementation-plan.md`.
2. Implementasikan vertical slice terkecil terlebih dahulu: upload → inspect → safe text edit → verify → preview → commit.
3. Setiap operasi mutasi wajib memiliki unit test, invariant test, dan fixture round-trip.
4. Jangan mengklaim native Mendeley support hanya karena XML berhasil dibuat. Capability tersebut baru aktif bila test di `docs/08-citation-mendeley-compatibility.md` lulus.
5. Jangan memasukkan bibliographic metadata hasil tebakan model.
6. Jangan mencatat isi dokumen atau API key ke log.
7. Semua path file, archive entry, URL resolver, dan AI output dianggap untrusted.
8. Tolak operasi ketika precondition tidak cocok; jangan melakukan fuzzy write secara diam-diam.
9. Kegagalan harus fail closed: file asli tetap tersedia dan proposal dibatalkan.
10. Pengguna selalu melihat diff, sumber yang digunakan, warnings, dan status verifikasi sebelum commit.

## Recommended repository layout

```text
app/
  main.py
  api/
  core/
  docx/
    package.py
    inspector.py
    fields.py
    anchors.py
    executor.py
    serializer.py
  references/
    intake.py
    parsers.py
    resolver.py
    dedupe.py
    retrieval.py
  agents/
    client.py
    scope.py
    planner.py
    verifier.py
  verification/
  storage/
  models/
frontend/
validator-dotnet/
tests/
fixtures/
```

## Completion report required from coding agent

Setiap milestone harus melaporkan:

- file yang dibuat/diubah;
- requirement yang dipenuhi;
- test yang dijalankan dan hasilnya;
- known limitations;
- capability flags yang aktif;
- risiko atau keputusan baru yang memerlukan ADR.
