# AI DOCX Academic Editor — Cloudflare Pages Frontend

Antarmuka web (Single-Page Application) yang didesain secara khusus untuk berkomunikasi secara *headless* dengan server backend Render (`https://docx-editor-8v0s.onrender.com`).

## Keunggulan
- **⚡ Zero Cold Start**: Antarmuka HTML/CSS/JS ini dimuat secara instan (< 1 detik) dari jaringan CDN global Cloudflare Pages.
- **🛠️ Tanpa Framework Berat**: Memakai Vanilla JavaScript murni tanpa perlu proses `npm build` atau konfigurasi rumit.
- **🎨 Glassmorphism & Dark Mode**: Desain UI modern, interaktif, dan mudah digunakan untuk revisi dokumen akademis.

## Cara Deploy Gratis ke Cloudflare Pages

### Opsi A: Upload Langsung (Drag & Drop) via Dashboard Cloudflare
1. Login ke akun [Cloudflare Dashboard](https://dash.cloudflare.com/) -> pilih menu **Workers & Pages**.
2. Klik tombol **Create application** -> pilih tab **Pages** -> klik **Upload assets**.
3. Beri nama proyek Anda (misal: `ai-docx-editor`).
4. Drag-and-drop seluruh folder `frontend` ini (yang berisi `index.html`, `style.css`, dan `app.js`) ke area upload Cloudflare.
5. Klik **Deploy site**. Selesai! Web UI Anda langsung aktif di URL `https://ai-docx-editor.pages.dev`.

### Opsi B: Hubungkan dengan GitHub Repository
Jika Anda ingin Cloudflare otomatis memperbarui UI setiap kali Anda melakukan `git push`:
1. Di halaman **Workers & Pages** -> klik **Connect to Git**.
2. Pilih repository `khoirulzz/docx-editor` dari GitHub Anda.
3. Di pengaturan build:
   - **Framework preset**: `None`
   - **Build command**: *(kosongkan)*
   - **Build output directory**: `frontend`
4. Klik **Save and Deploy**.

## Konfigurasi Endpoint Backend
Secara default, aplikasi web ini telah diarahkan ke backend Render Anda (`https://docx-editor-8v0s.onrender.com`). 
Jika sewaktu-waktu Anda ingin mengubah URL server backend (misal saat pengujian di `http://localhost:7860`), cukup klik tombol **⚙️ API Config** pada header kanan atas web UI.
