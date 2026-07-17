# Blueprint: AI Word Document Editor Tool

## 1. Tujuan Proyek
Membangun web tool yang memungkinkan user mengedit dokumen .docx (khususnya skripsi/dokumen akademik panjang) menggunakan AI sebagai agent, dengan:
- Edit bertarget per-bagian (misal hanya Bab III), bukan seluruh dokumen
- AI hanya mengusulkan rencana edit terstruktur (JSON), eksekusi dilakukan oleh kode deterministik — AI TIDAK PERNAH langsung menulis/memodifikasi XML
- Field sitasi Mendeley (CSL citation fields) di document.xml harus dideteksi, dipertahankan utuh kecuali user secara eksplisit minta diedit
- Ada tahap verifikasi sebelum perubahan final disimpan
- Efisiensi token: tidak pernah mengirim seluruh dokumen ke AI dalam satu request

**PENTING untuk AI agent pembangun**: ikuti arsitektur dan alur di bawah ini persis. Jangan mengganti pendekatan (misal: jangan biarkan AI menulis XML langsung, jangan kirim seluruh dokumen ke LLM, jangan pakai library yang mengabaikan field code Mendeley). Kalau ada keputusan implementasi kecil yang tidak dijelaskan di sini, boleh diputuskan sendiri, tapi arsitektur inti WAJIB diikuti.

## 2. Stack Teknologi
- **Frontend**: web app (bebas framework, sarankan single-page HTML/JS atau React) — upload docx, chat instruksi, preview diff, tombol accept/undo
- **Backend**: Hugging Face Space, Docker SDK (bukan Gradio), Python (FastAPI/Flask)
- **AI provider**: Blackbox AI API (user sudah punya API key + langganan) — panggil HANYA dari backend, jangan pernah expose API key ke frontend
- **XML processing**: `lxml` untuk manipulasi langsung `word/document.xml` di dalam docx (docx dibuka sebagai zip). `python-docx` boleh dipakai untuk baca teks biasa, TAPI TIDAK CUKUP untuk field sitasi Mendeley — itu wajib pakai lxml langsung ke XML

## 3. Mekanisme Field Sitasi Mendeley (WAJIB DIPAHAMI)
Mendeley Word plugin menyimpan sitasi sebagai field code di `document.xml`, bentuknya kombinasi elemen `w:fldChar` (type="begin"/"separate"/"end") dan `w:instrText` berisi teks `ADDIN CSL_CITATION` diikuti JSON (berisi `citationID`, `properties`, `citationItems` dengan data author/tahun/dll).

Aturan wajib:
- Saat parsing, deteksi dan tandai elemen ini sebagai "citation field" — simpan terpisah dari teks paragraf biasa
- Field yang tidak disebutkan dalam instruksi user WAJIB tetap identik byte-nya (tidak boleh ikut ter-reformat/ter-generate ulang oleh AI)
- Kalau user minta edit sitasi (tambah/ubah/hapus), edit dilakukan pada JSON di dalam `w:instrText`, lalu tulis ulang field dengan struktur field code yang sama (begin/separate/end tetap ada), supaya Mendeley masih mengenalinya saat dibuka ulang

## 4. Alur Kerja End-to-End
1. **Upload**: user upload .docx
2. **Parse awal**: backend buka docx sebagai zip, ambil `document.xml`, bangun representasi paragraf per-index, deteksi heading level (untuk deteksi bab: cari paragraf berstyle "Heading 1" yang cocok pola "BAB <angka/romawi>"), catat range index awal-akhir tiap bab. Tandai semua citation field dan index posisinya, simpan terpisah dari teks biasa.
3. **Simpan representasi ini di session** (server-side, keyed by session/file id) — supaya turn chat berikutnya tidak perlu re-parse & re-kirim ulang semua ke AI
4. **User kasih instruksi** (contoh: "tambah referensi di Bab III paragraf tentang X")
5. **Tahap outline (opsional, untuk dokumen panjang)**: kirim ke AI hanya outline ringkas (nomor bab + 1 baris ringkasan tiap bab/paragraf) → AI tentukan range/bagian mana yang relevan
6. **Tahap slice**: backend ambil HANYA teks paragraf dalam range yang relevan (misal Bab III saja) dari representasi tersimpan
7. **AI plan**: kirim slice + instruksi ke Blackbox API, minta balasan dalam JSON terstruktur berisi operasi edit (contoh: `{"operation": "replace_paragraph", "index": 42, "new_text": "..."}` atau `{"operation": "insert_after", "index": 40, "text": "..."}`). AI TIDAK mengembalikan XML mentah, hanya operasi terstruktur
8. **Eksekusi**: kode backend menerapkan operasi tersebut ke `document.xml` asli pada index yang sama persis dengan yang tercatat di langkah 2. Bagian di luar range (termasuk semua citation field di luar cakupan edit) tidak disentuh sama sekali
9. **Verifikasi deterministik** (selalu dijalankan): cek XML masih valid (well-formed), cek jumlah/isi citation field yang seharusnya tidak berubah memang identik dengan sebelum edit
10. **Verifikasi AI (opsional, hanya untuk edit kompleks/ambigu)**: panggil AI sekali lagi untuk cek apakah hasil edit sesuai instruksi user
11. **Preview**: tampilkan diff (before/after) ke user di frontend
12. **Confirm/undo**: kalau user accept, zip ulang seluruh isi docx (document.xml yang sudah diedit + semua file lain yang tidak berubah: styles.xml, numbering.xml, media, dll) jadi file .docx baru, siap didownload. Kalau undo, representasi kembali ke versi sebelumnya di session.

## 5. Strategi Efisiensi Token (WAJIB diterapkan)
- Jangan pernah kirim seluruh isi dokumen ke AI dalam satu request
- Gunakan pendekatan outline-first untuk dokumen panjang (>10 halaman): AI pilih bagian relevan dulu dari ringkasan, baru diberi teks lengkap bagian itu
- Simpan representasi dokumen di session backend; jangan re-kirim/re-parse ulang tiap giliran chat
- Verifikasi via AI hanya untuk kasus ambigu; edit sederhana cukup verifikasi deterministik (cek XML valid + citation field utuh)
- Kalau Blackbox API mendukung prompt caching, cache system prompt/instruksi aturan editing

## 6. Struktur Data yang Disimpan per Session
- `paragraphs`: list objek `{index, style (heading/normal/dst), text, xml_node_ref}`
- `chapters`: list objek `{title, start_index, end_index}`
- `citation_fields`: list objek `{index, raw_instrtext_json, xml_node_ref}`
- `file_id`/session id untuk mapping ke file docx asli yang tersimpan sementara (in-memory atau temp storage, karena HF Space free tier storage-nya ephemeral)

## 7. API Contract (garis besar, boleh disesuaikan detail teknisnya)
- `POST /upload` → terima file docx, return `session_id` + outline (daftar bab)
- `POST /chat` → terima `session_id` + instruksi user → return rencana edit + preview diff
- `POST /confirm` → terima `session_id` + approval → return file docx final (download link/blob)
- `POST /undo` → kembalikan session ke state sebelumnya

## 8. Batasan Lingkungan yang Perlu Diperhatikan
- HF Space free tier: cold start setelah idle (~30 detik), storage ephemeral (jangan andalkan penyimpanan permanen kecuali upgrade)
- API key Blackbox disimpan sebagai environment variable/secret di HF Space, jangan hardcode

## 9. Yang TIDAK boleh dilakukan
- AI tidak boleh langsung generate/menulis XML mentah untuk diterapkan langsung tanpa lewat kode eksekusi terstruktur
- Tidak boleh mengirim seluruh dokumen ke AI kalau dokumen panjang (>10 halaman) — wajib pakai slice/outline-first
- Tidak boleh mengubah/menghapus citation field yang tidak disebutkan dalam instruksi user
- Tidak boleh mengganti pendekatan arsitektur ini dengan pendekatan lain tanpa konfirmasi ke user
