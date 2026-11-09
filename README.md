# Scentra — Manual Unified Inbox

Workspace internal customer service untuk Scentra Parfume (oleh-oleh haji & herbal).
CS mencatat pesan pelanggan dari **Shopee, TikTok Shop, dan Lazada** ke satu antrean,
sistem mengklasifikasikan pesan dan menyusun rekomendasi balasan dari knowledge base toko.

> **Scentra tidak terhubung ke API marketplace mana pun.** Pesan dimasukkan manual oleh CS,
> dan balasan tetap dikirim CS melalui Seller Center masing-masing marketplace. Endpoint
> `GET /api/health` mengembalikan `"marketplace_api_connected": false` sebagai penegasan.

Dibuat untuk **COMPARE 2026 — Business Case Hackathon**, studi kasus
"Layanan Pelanggan dan Profitabilitas Produk pada Usaha Oleh-Oleh Haji".

---

## 1. Cara menjalankan

### Cara tercepat — Docker (disarankan)

```bash
docker compose up --build
```

Setelah ketiga kontainer siap, isi data sintetis:

```bash
docker compose exec backend python -m app.seed
```

Buka <http://localhost:3000>.

| Layanan    | Alamat                      |
| ---------- | --------------------------- |
| Frontend   | http://localhost:3000       |
| API        | http://localhost:8000       |
| Dokumentasi API (Swagger) | http://localhost:8000/docs |
| PostgreSQL | localhost:5432              |

### Tanpa Docker

**Backend** (Python 3.11+):

```bash
cd backend
python -m venv .venv
.venv/Scripts/activate        # Windows;  di Linux/macOS: source .venv/bin/activate
pip install -r requirements.txt
```

Siapkan database. Salin `.env.example` menjadi `.env`, lalu arahkan `DATABASE_URL` ke
PostgreSQL Anda. Untuk mencoba cepat tanpa memasang PostgreSQL, SQLite juga didukung:

```bash
# PostgreSQL
export DATABASE_URL="postgresql+psycopg://scentra:scentra@localhost:5432/scentra"
# atau SQLite, tanpa server apa pun
export DATABASE_URL="sqlite:///./scentra_dev.db"

python -m app.seed                                    # isi data sintetis
uvicorn app.main:app --reload --port 8000
```

**Frontend** (Node.js 20+):

```bash
cd frontend
npm install
cp .env.example .env.local          # NEXT_PUBLIC_API_URL=http://localhost:8000
npm run dev
```

### Akun demo

Seluruhnya data sintetis. Tidak ada data pelanggan nyata maupun kredensial toko.

| Peran      | Email                | Password     |
| ---------- | -------------------- | ------------ |
| CS         | ayu@scentra.test     | ayu12345     |
| CS         | bima@scentra.test    | bima12345    |
| Supervisor | rina@scentra.test    | rina12345    |
| Pemilik    | husin@scentra.test   | husin12345   |

---

## 2. Masalah yang dibantu

Dari studi kasus: CS berulang kali mengetik jawaban yang sama ("Ready, Kak?",
"Ada ukuran apa saja?", "Bisa dikirim hari ini?"), sehingga pembeli yang menyampaikan
**keluhan** justru menunggu lebih lama.

Scentra menangani tiga jenis pesan yang disebut studi kasus:

| Jenis pesan           | Contoh                                      | Yang dilakukan Scentra                                   |
| --------------------- | ------------------------------------------- | -------------------------------------------------------- |
| Pertanyaan umum       | "Ready, Kak?", "Ada ukuran apa saja?"        | Menyusun jawaban dari katalog, stok, dan aturan pengiriman |
| Keluhan               | "Kok yang dikirim 500 g?"                    | Diberi label komplain, prioritas tinggi, diteruskan ke staf |
| Informasi belum pasti | Stok atau cutoff tidak diketahui             | Tidak membuat klaim, meminta staf memeriksa lebih dulu     |

**Cakupan versi ini:** hanya Masalah 1 (layanan pelanggan). Masalah 2 studi kasus
(profitabilitas per produk dan per marketplace) belum dikerjakan dan tidak diklaim ada.

---

## 3. Cara kerja produk

```
┌──────────────┐   pesan disalin    ┌─────────────────────────────────────┐
│ Seller Center│ ─────manual──────► │ Next.js (App Router) + Tailwind     │
│  marketplace │                     │ login · inbox · detail · knowledge  │
└──────────────┘ ◄──balasan──────── └──────────────┬──────────────────────┘
       ▲          disalin CS                       │ REST + JWT
       │                                           ▼
       │                            ┌─────────────────────────────────────┐
       └────────────────────────────│ FastAPI                             │
         (di luar Scentra)          │  classify()  → intent + prioritas   │
                                    │  suggest()   → balasan + sumber     │
                                    └──────────────┬──────────────────────┘
                                                   │ SQLModel
                                                   ▼
                                    ┌─────────────────────────────────────┐
                                    │ PostgreSQL                          │
                                    │ percakapan · pesan · klasifikasi ·  │
                                    │ knowledge base · audit log          │
                                    └─────────────────────────────────────┘
```

### Klasifikasi pesan — `backend/app/nlp.py`

Aturan kata kunci, **bukan model bahasa**, supaya setiap keputusan bisa dijelaskan
baris per baris kepada juri dan diperbaiki tanpa melatih ulang apa pun.

Intent: `stock_inquiry`, `product_inquiry`, `shipping_inquiry`, `order_inquiry`,
`complaint`, `return_refund`, `other`, `unknown`.

Dua hal yang disengaja:

- **Komplain dan refund diperiksa lebih dulu.** Kalimat "beli 1 kg kok yang dikirim 500 g,
  kecewa banget" mengandung kata "dikirim", tetapi tetap diklasifikasikan sebagai komplain,
  bukan pertanyaan pengiriman.
- **Variasi penulisan ditoleransi.** "ready / redy / redi", "100 g / 100g / 100gr",
  "1 kg / 1kg" dicocokkan ke varian yang sama.

Pesan yang tidak dikenali tetap tersimpan dengan intent `unknown`, dan CS dapat mengoreksi
intent. Koreksi disimpan (`classifications.corrected_by`) untuk mengukur akurasi.

### Suggested reply — aturan yang menjaga sistem tidak berbohong

Rekomendasi hanya boleh menyatakan fakta yang ada di knowledge base:

| Kondisi knowledge base                   | Perilaku                                                        |
| ---------------------------------------- | --------------------------------------------------------------- |
| Stok tercatat dan diperbarui < 48 jam    | Menyatakan tersedia / kosong, menampilkan sumber dan waktu       |
| Stok **belum tercatat**                  | Tidak menyatakan ada maupun habis, minta verifikasi staf         |
| Stok **lebih tua dari 48 jam**           | Ditandai kedaluwarsa, minta konfirmasi sebelum dijanjikan        |
| Aturan pengiriman marketplace kosong     | Jawaban aman, minta verifikasi                                   |
| Komplain                                 | Prioritas tinggi, template generik tidak dipakai                 |
| Retur/refund                             | Eskalasi ke supervisor (aturan refund belum ada di KB)           |
| Tidak dikenali                           | Jawaban menahan waktu, minta staf memeriksa                      |

Setiap rekomendasi menampilkan **sumbernya** sebagai chip, misalnya
`STOK · 1 kg · 24 pcs · 3 jam lalu` atau `FAQ · Apakah produk bersertifikat halal?`.

### Batas yang ditegakkan sistem

- Tombol **Salin teks** tidak mengubah status percakapan. Menyalin bukan berarti terkirim.
- Status di Scentra adalah pencatatan internal, bukan bukti pesan terkirim di marketplace.
- Dua pelanggan bernama sama **tidak pernah** digabung. Pengenal utama adalah referensi
  percakapan/order, bukan nama.
- Pesan dengan referensi yang sudah ada memicu peringatan duplikasi sebelum CS menyimpan.
- Kegagalan klasifikasi tidak membatalkan penyimpanan pesan.

---

## 4. Pengujian

```bash
cd backend
.venv/Scripts/python.exe -m pytest -q       # Windows
python -m pytest -q                          # Linux/macOS
```

**39 pengujian, seluruhnya lulus.** Tidak memerlukan PostgreSQL — pengujian API memakai
SQLite sementara.

- `tests/test_nlp.py` — skenario TC-01 … TC-07 dari PRD, pencocokan varian, dan jaminan
  bahwa balasan tidak pernah mengklaim stok yang tidak diketahui.
- `tests/test_api.py` — acceptance criteria AC-01, AC-02, AC-03, AC-07, AC-09, AC-10,
  ditambah hak akses, validasi, catatan internal, dan audit log.

Pemetaan skenario studi kasus:

| ID      | Input                                   | Kondisi KB                | Hasil yang diuji                       |
| ------- | --------------------------------------- | ------------------------- | -------------------------------------- |
| TC-01   | "Kak, kurma Ajwa 1 kg ready?"           | Stok ada dan valid        | Stock inquiry, jawaban sesuai stok     |
| TC-02   | "Kak, kurma Ajwa 250 g ready?"          | Stok belum tercatat       | Minta verifikasi, tanpa klaim          |
| TC-02b  | "Kacang arab 500 g ready?"              | Stok > 48 jam             | Ditandai kedaluwarsa, minta konfirmasi |
| TC-03   | "Cokelat Turki ada ukuran apa saja?"    | Varian tersedia           | Product inquiry, varian ditampilkan    |
| TC-04   | "Bisa dikirim hari ini?" (Shopee)       | Cutoff tersedia           | Jawaban sesuai aturan cutoff           |
| TC-04b  | "Bisa dikirim hari ini?" (Lazada)       | Aturan kosong             | Eskalasi                               |
| TC-05   | "Barang saya rusak, kecewa banget"      | —                         | Complaint, prioritas tinggi            |
| TC-06   | "Saya mau refund"                       | Aturan refund tidak ada   | Return/refund, eskalasi                |
| TC-07   | Pesan tidak dikenal                     | Tidak ada FAQ relevan     | Unknown, tetap disimpan                |
| TC-08   | Referensi sama dimasukkan dua kali      | —                         | Peringatan duplikasi, pesan digabung   |
| TC-09   | Dua pelanggan bernama sama              | Referensi berbeda         | Tetap dua percakapan terpisah          |
| TC-10   | Suggested reply disalin                 | —                         | Status tidak berubah jadi resolved     |

---

## 5. Data uji

Data sintetis di `backend/app/seed.py`: 4 pengguna, 12 percakapan, 4 produk
(9 varian), 4 FAQ, dan aturan pengiriman tiga marketplace.

Tiga kondisi sengaja dibuat tidak lengkap untuk memperlihatkan perilaku eskalasi:

- **Kurma Ajwa 250 g** — stok belum pernah tercatat.
- **Kacang Arab 500 g** — stok terakhir diperbarui 90 jam lalu (kedaluwarsa).
- **Lazada** — aturan pengiriman kosong.

---

## 6. Susunan berkas

```
backend/
  app/
    main.py        FastAPI, CORS, startup
    db.py          engine SQLModel (PostgreSQL, SQLite untuk pengujian)
    models.py      tabel sesuai PRD bab 11
    schemas.py     validasi request/response
    auth.py        PBKDF2 password hashing, JWT, RBAC
    nlp.py         classify() dan suggest() — fungsi murni, tanpa database
    services.py    jembatan database ↔ nlp, audit log
    routes.py      seluruh endpoint /api
    seed.py        data sintetis
  tests/           39 pengujian
frontend/
  src/app/
    login/                    halaman masuk
    (app)/layout.tsx          sidebar + topbar
    (app)/dashboard/          ringkasan operasional
    (app)/inbox/              unified inbox, detail, form tambah
    (app)/knowledge/          FAQ, produk/stok, pengiriman, eskalasi
  src/lib/api.ts              klien REST
  src/lib/ui.tsx              komponen dan token tampilan
docker-compose.yml
```

---

## 7. Teknologi

| Lapisan  | Teknologi                              |
| -------- | -------------------------------------- |
| Frontend | Next.js 16 (App Router), React 19, TypeScript, Tailwind CSS 4 |
| Backend  | Python, FastAPI, SQLModel              |
| Database | PostgreSQL 16 (SQLite untuk pengujian) |
| Auth     | JWT, PBKDF2-HMAC-SHA256                |
| Pengujian| Pytest                                 |

Tidak ada layanan AI berbayar, tidak ada kuota pihak ketiga, dan tidak ada API marketplace.
Seluruh klasifikasi berjalan lokal dengan aturan di `nlp.py`.

---

## 8. Yang belum dikerjakan

Disebutkan terbuka, bukan disembunyikan:

- **Masalah 2 studi kasus** (profitabilitas per produk/marketplace) belum dibuat.
- Halaman manajemen pengguna dan form CRUD knowledge base belum ada; knowledge base
  masih tampil baca-saja dan diisi lewat `seed.py`.
- Belum ada migrasi database (Alembic); skema dibuat dengan `create_all` saat startup.
- Pengujian UI otomatis (Playwright) belum ada; alur UI diuji manual.
- Prototipe diverifikasi end-to-end di atas SQLite. Jalur PostgreSQL disediakan lewat
  `docker-compose.yml` dengan kode yang sama (SQLModel), tetapi belum dijalankan penulis
  pada mesin uji karena Docker tidak aktif saat pengembangan.

---

## 9. Catatan penggunaan AI

Sesuai ketentuan Guidebook COMPARE 2026:

| Yang disebutkan      | Penjelasan                                                                    |
| -------------------- | ----------------------------------------------------------------------------- |
| Alat dan kegunaan    | Claude (Anthropic) membantu penyusunan rancangan, penulisan kode, dan dokumentasi. |
| Bagian yang digunakan| Kerangka backend/frontend, aturan klasifikasi awal, penulisan pengujian, README. |
| Pemeriksaan tim      | Seluruh kode dibaca dan dijalankan tim; aturan klasifikasi dan isi knowledge base disesuaikan dengan studi kasus, lalu diverifikasi lewat 39 pengujian otomatis. |
| Hak dan biaya        | Tidak memakai layanan AI berbayar di dalam produk. Produk berjalan tanpa kuota pihak ketiga. |

---

## 10. Privasi

Seluruh nama, nomor pesanan, dan angka pada data uji dibuat sendiri dan tidak mewakili
pelanggan, harga, atau transaksi nyata. Scentra tidak menyimpan password, cookie, atau
token akun marketplace. Password pengguna disimpan sebagai hash PBKDF2, bukan teks biasa.
