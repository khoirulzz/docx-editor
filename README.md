---
title: AI DOCX Academic Editor
emoji: 📝
colorFrom: blue
colorTo: indigo
sdk: docker
app_port: 7860
---
# AI DOCX Academic Editor — Agent Workspace Specification

Versi spesifikasi: **1.0.0**  
Tanggal pembekuan: **2026-07-17**  
Bahasa requirement: Indonesia; identifier teknis: English.

Paket ini adalah sumber kebenaran untuk membangun web application yang dapat membaca, melihat, menganalisis, dan memodifikasi dokumen `.docx` panjang melalui instruksi chat, dengan perlindungan struktur Office Open XML dan alur sitasi akademik yang dapat diaudit.

## Mulai dari sini

Coding agent wajib membaca dalam urutan berikut:

1. `AGENTS.md`
2. `docs/00-product-scope.md`
3. `docs/01-non-negotiable-requirements.md`
4. `docs/02-architecture.md`
5. `docs/03-docx-domain-model.md`
6. `docs/04-docx-inspection-parsing.md`
7. `docs/05-edit-plan-protocol.md`
8. `docs/06-deterministic-executor.md`
9. `docs/07-reference-intake-evidence.md`
10. `docs/08-citation-mendeley-compatibility.md`
11. `docs/09-verification-invariants.md`
12. `docs/10-security-privacy-threat-model.md`
13. `api/openapi.yaml`
14. `schemas/*.json`
15. `docs/18-implementation-plan.md`
16. `docs/19-definition-of-done.md`

## Prinsip inti

- LLM adalah **planner**, bukan XML writer.
- File asli immutable; perubahan dibuat sebagai proposal version.
- Seluruh output LLM divalidasi schema dan kebijakan sebelum dieksekusi.
- Identitas target memakai stable anchors dan precondition hash, bukan paragraph index saja.
- Existing managed citation harus dipertahankan.
- Reference notes user boleh tidak terstruktur; sistem yang mengekstrak, menormalisasi, mencocokkan, dan memverifikasi.
- Sitasi baru hanya boleh memakai reference/evidence yang tersedia atau telah diverifikasi.
- Native managed-Mendeley insertion adalah capability yang harus melewati compatibility gate; sistem tidak boleh menyatakan dukungan sebelum fixture test lulus.
- Selalu tersedia safe fallback: formatted CSL citation + structured placeholder/manifest + BibTeX/RIS export.

## Struktur paket

- `docs/`: requirement dan desain lengkap.
- `schemas/`: JSON Schema yang menjadi kontrak machine-readable.
- `api/`: OpenAPI contract.
- `prompts/`: system prompt agent runtime.
- `skills/`: skill instructions untuk coding/maintenance agent.
- `examples/`: contoh input-output yang representatif.
- `tests/`: fixture matrix dan acceptance scenarios.
- `decisions/`: Architecture Decision Records.
- `config/`: contoh konfigurasi environment.
- `legacy/`: blueprint awal untuk referensi historis, bukan sumber kebenaran.

## Makna kata normatif

- **MUST/WAJIB**: tidak boleh dilanggar.
- **MUST NOT/DILARANG**: tidak boleh dilakukan.
- **SHOULD/SEBAIKNYA**: boleh berbeda hanya dengan alasan tertulis dan test.
- **MAY/BOLEH**: opsional.

## Catatan penting kompatibilitas Mendeley

Tidak ada dokumentasi publik yang cukup untuk menjamin bahwa field buatan aplikasi akan selalu dikenali oleh seluruh versi Mendeley Cite. Karena itu paket ini mendesain adapter native, fixture harvesting, dan capability gate. Preservation existing fields adalah requirement produksi; insertion native baru dianggap produksi setelah round-trip test Word/Mendeley lulus.
