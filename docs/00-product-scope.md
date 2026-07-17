# Product Scope

## 1. Product vision

Web editor berbasis chat untuk dokumen akademik `.docx`, khususnya skripsi/tesis/laporan panjang. User mengunggah dokumen utama dan bahan referensi dalam format apa pun yang didukung, lalu memberi instruksi natural seperti:

> Perbaiki Bab II, perkaya dengan sumber dari file pendukung, gunakan APA 7, utamakan parafrasa, pertahankan format dan sitasi Mendeley.

Sistem memilih scope relevan, membuat edit plan, mengeksekusi perubahan secara deterministik, memverifikasi struktur dan sitasi, lalu menampilkan preview yang dapat diterima atau ditolak.

## 2. Primary user experience

User cukup melakukan:

1. upload satu `.docx` utama;
2. opsional upload `.txt`, `.md`, `.bib`, `.ris`, `.csv`, `.json`, `.docx` catatan, atau PDF sumber;
3. memberi instruksi chat biasa;
4. memeriksa proposal dan citation report;
5. accept/reject per operasi atau seluruh proposal;
6. download `.docx` hasil dan optional citation bundle.

User **tidak wajib** mengisi Reference ID, citation key, CSL-JSON, DOI, atau schema internal. Sistem membuat identifier internal dan meminta klarifikasi hanya bila terdapat ambiguitas material.

## 3. Functional scope

### 3.1 Document understanding

- membaca package DOCX dan seluruh story yang didukung;
- membangun outline, chapter/subchapter, paragraph/run map, table map, field map, protected-node map;
- menampilkan teks dan struktur untuk preview;
- mengenali Bahasa Indonesia dan pola BAB/subbab custom.

### 3.2 Flexible edits

- proofreading dan perbaikan tata bahasa;
- rewrite/paraphrase/expand/shorten;
- insert before/after;
- span replacement dengan format inheritance;
- paragraph insertion/deletion dengan guard;
- heading/style change yang eksplisit;
- table-cell text edits pada scope aman;
- citation insertion request;
- bibliography refresh/creation pada mode yang didukung;
- undo/version history.

### 3.3 Reference enrichment

- ingest loose notes dan file bibliografi;
- ekstrak candidate references dan evidence;
- verifikasi metadata via DOI/title resolver;
- deduplicate;
- retrieve/rerank evidence yang relevan;
- larang source hallucination;
- citation provenance dan evidence trace.

### 3.4 Citation output modes

1. `preserve_only`: existing managed citations dijaga; sumber baru tidak diinsert.
2. `formatted_csl`: citation dan bibliography diformat deterministik dengan CSL, tetapi bukan managed Mendeley object.
3. `placeholder_manifest`: placeholder terstruktur + manifest + `.bib/.ris` untuk finalisasi Mendeley.
4. `native_mendeley_legacy`: adapter legacy `ADDIN CSL_CITATION`, capability-gated.
5. `native_mendeley_cite`: adapter modern, capability-gated dan tidak boleh diasumsikan identik dengan legacy.

Mode 4–5 hanya boleh ditawarkan jika compatibility test untuk producer/version yang bersangkutan lulus.

## 4. Non-goals initial release

- pixel-perfect browser rendering setara Microsoft Word;
- mengubah seluruh Office feature secara bebas;
- otomatis menyelesaikan konflik track changes yang kompleks;
- menjamin pagination identik lintas OS/Word version;
- menjamin integrasi private/undocumented Mendeley tanpa fixture test;
- menggantikan pemeriksaan akademik manusia;
- mengakses full text berbayar tanpa izin.

## 5. Success metrics

- 100% file asli tidak pernah ditimpa.
- 100% AI responses untuk mutasi melewati schema validation.
- 100% untouched protected fields mempertahankan required fingerprints.
- 0 sumber bibliografis dibuat tanpa provenance.
- >95% proposal sederhana dapat dieksekusi tanpa manual repair pada fixture suite.
- 100% native citation capability dinonaktifkan bila compatibility gate gagal.
- user dapat menyelesaikan alur utama tanpa menulis metadata teknis.
