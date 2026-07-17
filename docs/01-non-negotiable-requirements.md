# Non-Negotiable Requirements

## A. LLM boundary

1. LLM MUST NOT menerima atau menghasilkan XML untuk diterapkan.
2. LLM hanya menghasilkan object sesuai `schemas/edit-plan.schema.json` atau schema agent lain.
3. Output LLM dianggap untrusted dan wajib melalui: JSON parse → schema validation → semantic validation → policy validation → precondition validation.
4. Sistem tidak boleh mengirim seluruh dokumen panjang secara default. Context selection wajib token-budget based.
5. LLM tidak boleh membuat bibliographic identity baru. Ia hanya boleh memilih `reference_id` yang diberikan atau mengeluarkan `unresolved_reference_request`.

## B. Original-file safety

1. Upload asli immutable dan content-addressed.
2. Semua perubahan dibuat pada proposal copy/version.
3. Commit bersifat atomic.
4. Bila verifikasi gagal, hasil tidak boleh tersedia sebagai final tanpa label unsafe dan explicit developer override; production UI tidak menawarkan override.
5. Undo dilakukan dengan version pointer, bukan reverse-edit buatan LLM.

## C. DOCX structural safety

1. Package diproses sebagai OPC/ZIP package, bukan hanya `document.xml`.
2. Parser harus menginventarisasi stories/parts yang relevan.
3. Paragraph index hanya ordinal display; bukan primary key.
4. Gunakan `w14:paraId` bila tersedia, ditambah fallback stable locator dan hashes.
5. Executor tidak boleh mengganti seluruh paragraf yang mengandung field, hyperlink, drawing, bookmark, comment range, footnote reference, revision, equation, content control, atau mixed formatting tanpa operation khusus dan explicit policy.
6. Existing complex field harus diparse dengan state machine begin/separate/end dan support nesting.
7. Unrelated package parts dan ZIP entries harus disalin tanpa perubahan.

## D. Citation safety

1. Existing managed citation fields harus terdeteksi dan diproteksi.
2. Untouched citation fields diverifikasi menggunakan exact instruction-text hash, canonical subtree hash, result-text hash, boundary signature, dan relative anchor.
3. Native insertion tidak boleh aktif hanya berdasarkan keberhasilan XML parse.
4. Citation style display harus di-render deterministik oleh CSL engine; jangan meminta LLM menulis punctuation APA secara bebas sebagai source of truth.
5. Direct quote wajib memiliki locator/page atau warning blocking sesuai policy.
6. Citation baru harus memiliki provenance dan evidence association.
7. Bibliography impact harus ditampilkan di preview.

## E. Reference intake UX

1. User boleh upload catatan bebas yang tidak terstruktur.
2. Sistem membuat reference IDs dan evidence IDs otomatis.
3. Missing metadata tidak boleh diisi dengan tebakan.
4. Resolver result memiliki confidence dan source.
5. Ambiguity material dipresentasikan dalam UI; sumber unresolved tidak boleh menjadi citation final.

## F. Security/privacy

1. API key hanya backend secret.
2. Dokumen dan reference text tidak masuk application logs.
3. XML parser: no network, no entity resolution, bounded input.
4. ZIP extraction harus mencegah zip bomb, path traversal, duplicate dangerous entries, dan oversized expansion.
5. Session IDs cryptographically random; endpoint resource access harus authorization-scoped.
6. File memiliki TTL dan deletion job.
7. Blackbox requests sebaiknya memakai per-request ZDR ketika tersedia dan requirement privacy mengharuskan.

## G. User control

1. Tidak ada commit tanpa explicit approval.
2. UI menampilkan before/after, warnings, source usage, citation mode, dan verification summary.
3. User dapat menerima/menolak per operation.
4. Perubahan yang dependent harus dikelompokkan dan tidak boleh diterima sebagian secara tidak konsisten.
