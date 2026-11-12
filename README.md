# ResponIn — Manual Unified Inbox

Workspace internal untuk Scentra Parfume (oleh-oleh haji & herbal), menjawab dua masalah
pada studi kasus COMPARE 2026:

1. **Layanan pelanggan.** CS mencatat pesan dari **Shopee, TikTok Shop, dan Lazada** ke
   satu antrean. Sistem mengklasifikasikan pesan dan menyusun rekomendasi balasan dari
   knowledge base toko, sehingga keluhan tidak tertimbun pertanyaan berulang.
2. **Profitabilitas produk.** Pemilik melihat laba per produk, per marketplace, dan per
   periode setelah komisi, voucher, ongkir yang ditanggung penjual, dan retur.

> **ResponIn tidak terhubung ke API marketplace mana pun.** Pesan dimasukkan manual oleh CS,
> dan balasan tetap dikirim CS melalui Seller Center masing-masing marketplace. Endpoint
> `GET /api/health` mengembalikan `"marketplace_api_connected": false` sebagai penegasan.

Dibuat untuk **COMPARE 2026 — Business Case Hackathon**, studi kasus
"Layanan Pelanggan dan Profitabilitas Produk pada Usaha Oleh-Oleh Haji".

Kebutuhan produk, aturan bisnis, model data, dan acceptance criteria ada di
[PRD.md](PRD.md). Cara memakai aplikasinya ada di bab 2.

---

## 1. Cara menjalankan

### Demo daring

Versi yang sudah ter-deploy, siap dibuka tanpa memasang apa pun:

| | Alamat |
| --- | --- |
| Aplikasi | https://scentra-khph.vercel.app |
| API | https://scentra-pi.vercel.app |
| Dokumentasi API (Swagger) | https://scentra-pi.vercel.app/docs |

Akun demo ada di akhir bab ini. Permintaan pertama setelah beberapa menit menganggur bisa
butuh beberapa detik karena fungsi serverless-nya tidur saat tidak dipakai.

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

### Deploy ke Vercel

Repositori ini berisi dua aplikasi, jadi dibuat **dua proyek Vercel dari repo yang
sama**, dibedakan lewat *Root Directory*. Database memakai Postgres terkelola
karena fungsi serverless tidak punya penyimpanan tetap — berkas SQLite akan hilang
setiap fungsi dimatikan.

**1. Buat database.** Di dasbor Vercel: **Storage → Create Database → Neon
(Postgres)**. Salin nilai `DATABASE_URL` yang diberikan.

**2. Isi data sintetis dari komputer sendiri** (sekali saja; perintah ini juga yang
membuat seluruh tabel):

```bash
cd backend
DATABASE_URL="<DATABASE_URL dari langkah 1>" python -m app.seed
```

**3. Deploy API.** **Add New → Project →** pilih repo ini → **Root Directory:
`backend`**. Vercel mengenali FastAPI sendiri lewat `app/main.py`, jadi
*Build and Output Settings* dibiarkan apa adanya. Tambahkan *Environment
Variables*:

| Nama           | Nilai                                                      |
| -------------- | ---------------------------------------------------------- |
| `DATABASE_URL` | dari langkah 1                                             |
| `SECRET_KEY`   | teks acak panjang, mis. hasil `openssl rand -hex 32`       |
| `CORS_ORIGINS` | sementara isi `http://localhost:3000`, diperbaiki di bawah |

Setelah deploy, catat alamatnya, lalu pastikan
`https://<api>.vercel.app/api/health` membalas `{"status":"ok"}`.

**4. Deploy frontend.** **Add New → Project →** repo yang sama → **Root Directory:
`frontend`** → *Environment Variable* `NEXT_PUBLIC_API_URL` =
`https://<api>.vercel.app` (tanpa garis miring di akhir).

**5. Tutup CORS.** Kembali ke proyek API, ubah `CORS_ORIGINS` menjadi alamat
frontend (`https://<frontend>.vercel.app`) lalu **Redeploy**. Tanpa langkah ini
browser menolak seluruh permintaan dari frontend.

Catatan: `NEXT_PUBLIC_API_URL` ditanam saat *build*, bukan dibaca saat aplikasi
jalan, jadi setiap kali nilainya berubah frontend harus di-*redeploy*.

### Akun demo

Seluruhnya data sintetis. Tidak ada data pelanggan nyata maupun kredensial toko.

| Peran      | Email                | Password     |
| ---------- | -------------------- | ------------ |
| CS         | ayu@scentra.test     | ayu12345     |
| CS         | bima@scentra.test    | bima12345    |
| Pemilik    | husin@scentra.test   | husin12345   |

---

## 2. Panduan pemakaian

Ada dua peran, dan keduanya memakai aplikasi ini untuk hal yang berbeda. CS
menghabiskan waktunya di Unified Inbox. Pemilik usaha membaca inbox tanpa mengubahnya,
dan yang sering dia buka adalah Profitabilitas.

Tidak ada satu akun yang mencakup semuanya, karena itu memang yang dibatasi. Untuk
mencoba alur chat, masuk sebagai Ayu. Untuk laporan laba, masuk sebagai Husin.

### Menangani satu chat, dari awal sampai selesai

Peran: CS.

**1. Salin pesan pembeli dari Seller Center.** ResponIn tidak menarik chat sendiri, jadi
pesannya disalin manual.

**2. Buka Unified Inbox, klik "+ Tambah percakapan".** Isi marketplace, nama pembeli,
nomor pesanan atau chat, produk yang ditanyakan bila sudah jelas, lalu tempel isi
pesannya. Marketplace, nama, dan isi pesan wajib diisi.

Kalau nomor pesanan itu sudah pernah dicatat, ResponIn memperingatkan dan menawarkan
menggabungkan pesan ke percakapan yang sudah ada. Terima tawaran itu, supaya satu pembeli
tidak terpecah jadi dua antrean. Dua pembeli bernama sama tidak pernah digabung, karena
yang dipakai sebagai pengenal adalah nomornya.

**3. Klik "Simpan pesan".** ResponIn langsung memberi label intent dan prioritas, lalu
menyusun rekomendasi balasan.

**4. Baca rekomendasinya beserta sumbernya.** Di bawah teks balasan ada chip kecil
seperti `STOK · 1 kg · 24 pcs · 3 jam lalu` atau `FAQ · Apakah produk bersertifikat
halal?`. Chip itu memberi tahu dari mana kalimatnya berasal. Kalau tidak ada chip yang
mendukung sebuah pernyataan, jangan kirim pernyataan itu.

**5. Sunting bila perlu, lalu klik "Salin teks".** Teksnya masuk ke papan klip. Status
percakapan sengaja tidak berubah, karena menyalin belum berarti terkirim.

**6. Tempel balasannya di Seller Center dan kirim dari sana.**

**7. Kembali ke ResponIn, catat tindakannya, lalu ubah statusnya.** Misalnya tulis
"balasan dikirim lewat Seller Center", lalu ubah status jadi Waiting for Customer atau
Resolved. Semua perubahan ini masuk ke riwayat aktivitas di bagian bawah halaman.

### Kalau rekomendasinya ditandai perlu verifikasi

Artinya ResponIn tidak punya data yang cukup, jadi dia sengaja tidak menjanjikan apa pun.
Alasannya tertulis di sebelah penandanya. Tiga yang paling sering muncul:

Stok varian itu belum pernah dicatat, jadi ResponIn tidak menyatakan tersedia maupun
habis. Cek stok fisik dulu, baru balas.

Stok tercatat tapi umurnya lebih dari 48 jam. Angkanya ditampilkan, tapi balasannya
meminta konfirmasi dulu karena bisa saja sudah berubah.

Aturan pengiriman marketplace itu belum diisi, misalnya cutoff Lazada. Pertanyaan
pengiriman ditahan untuk diperiksa pemilik usaha.

Penandaan ini bisa dipakai sebagai filter di daftar percakapan, supaya yang butuh
pengecekan manusia bisa dikumpulkan sekaligus.

### Kalau labelnya salah

Pada panel Klasifikasi, pilih intent yang benar. Rekomendasi balasannya langsung disusun
ulang, dan koreksinya tersimpan beserta nama yang mengoreksi. Catatan itu yang nanti
dipakai mengukur seberapa sering aturannya meleset.

### Membagi dan menyaring antrean

Menugaskan percakapan ke anggota tim lewat panel Status di halaman detail. Sesama CS
boleh saling menugaskan, dan setiap penugasan tercatat di riwayat.

Menyaring antrean menurut marketplace, status, atau penandaan perlu verifikasi, untuk
melihat mana yang menumpuk. Kotak pencarian menerima nama, nomor pesanan, maupun potongan
isi pesan.

### Membaca laporan profitabilitas

Peran: pemilik usaha. Menu ini tidak muncul bagi CS.

Di atas ada filter periode (30 hari, 90 hari, atau semua) dan filter marketplace. Di
bawahnya lima kartu: penjualan bersih, total biaya, laba, margin, dan jumlah transaksi
yang datanya belum lengkap.

Empat tab di bawahnya:

**Per produk** memperlihatkan produk mana yang menyumbang laba. Ini tab yang menjawab
pertanyaan Husin. Klik nama produk untuk langsung melihat transaksi penyusunnya.

**Per marketplace** membandingkan Shopee, TikTok Shop, dan Lazada setelah potongan
masing-masing.

**Rincian transaksi** menampilkan satu baris per pesanan, lengkap dengan komisi, voucher,
ongkir, dan modalnya. Jumlah kolom laba di sini selalu sama dengan angka di ringkasan.

**Modal & tarif** memperlihatkan modal per varian dan tarif potongan tiap marketplace,
termasuk mana yang belum diisi.

Dua tanda yang perlu dibaca benar. Tanda hubung berarti nilainya belum dicatat, bukan nol.
Tulisan "belum bisa dihitung" berarti ada komponen biaya yang hilang, sehingga baris itu
dikeluarkan dari total supaya tidak membuat produknya terlihat lebih untung daripada
kenyataannya.

Pada data demo, Cokelat Turki sengaja dibiarkan tanpa modal dan Lazada tanpa tarif
potongan, supaya perilaku ini langsung terlihat.

### Memasukkan data penjualan baru

Klik "Impor CSV" di halaman Profitabilitas. Format kolomnya ada di bab 6.

Sel yang dikosongkan pada kolom biaya berarti belum diketahui, dan barisnya ditandai belum
lengkap. Kalau voucher memang nol, tulis `0`, jangan dikosongkan. Dua hal itu diperlakukan
berbeda dan memang disengaja.

Baris yang bermasalah tidak menggagalkan seluruh berkas. Yang sah tetap tersimpan, dan
yang gagal dilaporkan satu per satu beserta alasannya. Pesanan yang nomornya sudah pernah
masuk akan ditolak, supaya satu penjualan tidak terhitung dua kali.

### Knowledge base

Halaman ini baca-saja untuk sekarang. Isinya FAQ, katalog produk beserta stok dan kapan
terakhir diperbarui, aturan pengiriman tiap marketplace, dan aturan eskalasi. Dari sinilah
rekomendasi balasan mengambil bahan, jadi kualitas jawabannya mengikuti kelengkapan
halaman ini.

Penambahan dan penyuntingan isinya masih lewat `backend/app/seed.py`. Form penyuntingannya
belum dibuat, dan itu tercatat di bab 9.

---

## 3. Masalah yang dibantu

### Masalah 1 — pertanyaan berulang di chat

Dari studi kasus: CS berulang kali mengetik jawaban yang sama ("Ready, Kak?",
"Ada ukuran apa saja?", "Bisa dikirim hari ini?"), sehingga pembeli yang menyampaikan
**keluhan** justru menunggu lebih lama.

ResponIn menangani tiga jenis pesan yang disebut studi kasus:

| Jenis pesan           | Contoh                                      | Yang dilakukan ResponIn                                   |
| --------------------- | ------------------------------------------- | -------------------------------------------------------- |
| Pertanyaan umum       | "Ready, Kak?", "Ada ukuran apa saja?"        | Menyusun jawaban dari katalog, stok, dan aturan pengiriman |
| Keluhan               | "Kok yang dikirim 500 g?"                    | Diberi label komplain, prioritas tinggi, diteruskan ke staf |
| Informasi belum pasti | Stok atau cutoff tidak diketahui             | Tidak membuat klaim, meminta staf memeriksa lebih dulu     |

### Masalah 2 — keuntungan per produk belum jelas

Omzet besar belum berarti untung. Setiap marketplace memotong komisi, voucher, ongkir
yang ditanggung penjual, dan retur dengan besaran berbeda, sehingga pemilik sulit tahu
produk mana yang benar-benar menguntungkan.

ResponIn menghitung laba per produk, per marketplace, dan per periode dari transaksi
yang dimasukkan manual atau diimpor dari berkas CSV. Dua aturan menentukan rancangannya:

- **Data kosong bukan nol.** Transaksi yang modal produknya atau tarif potongannya belum
  dicatat tidak dihitung labanya, ditandai *belum lengkap*, dan dikeluarkan dari total.
  Menganggapnya nol akan membuat produk terlihat jauh lebih untung daripada kenyataannya.
- **Angka harus dapat ditelusuri.** Setiap baris ringkasan bisa dibuka sampai ke
  transaksi aslinya, lengkap dengan rincian penjualan bersih, komisi, voucher, ongkir,
  dan modal. Jumlah rincian selalu sama dengan ringkasannya.

Laporan ini hanya dapat dibuka **pemilik usaha**; CS tidak melihat margin.

---

## 4. Cara kerja produk

```
┌──────────────┐   pesan disalin    ┌─────────────────────────────────────┐
│ Seller Center│ ─────manual──────► │ Next.js (App Router) + Tailwind     │
│  marketplace │                     │ login · inbox · detail · knowledge  │
└──────────────┘ ◄──balasan──────── └──────────────┬──────────────────────┘
       ▲          disalin CS                       │ REST + JWT
       │                                           ▼
       │                            ┌─────────────────────────────────────┐
       └────────────────────────────│ FastAPI                             │
         (di luar ResponIn)          │  classify()  → intent + prioritas   │
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
| Retur/refund                             | Ditahan untuk diperiksa pemilik (aturan refund belum ada di KB)  |
| Tidak dikenali                           | Jawaban menahan waktu, minta staf memeriksa                      |

Setiap rekomendasi menampilkan **sumbernya** sebagai chip, misalnya
`STOK · 1 kg · 24 pcs · 3 jam lalu` atau `FAQ · Apakah produk bersertifikat halal?`.

### Batas yang ditegakkan sistem

- Tombol **Salin teks** tidak mengubah status percakapan. Menyalin bukan berarti terkirim.
- Status di ResponIn adalah pencatatan internal, bukan bukti pesan terkirim di marketplace.
- Dua pelanggan bernama sama **tidak pernah** digabung. Pengenal utama adalah referensi
  percakapan/order, bukan nama.
- Pesan dengan referensi yang sudah ada memicu peringatan duplikasi sebelum CS menyimpan.
- Kegagalan klasifikasi tidak membatalkan penyimpanan pesan.

---

## 5. Pengujian

```bash
cd backend
.venv/Scripts/python.exe -m pytest -q       # Windows
python -m pytest -q                          # Linux/macOS
```

**78 pengujian, seluruhnya lulus.** Tidak memerlukan PostgreSQL — pengujian API memakai
SQLite sementara.

Masalah 1 — layanan pelanggan:

- `tests/test_nlp.py` — skenario TC-01 … TC-07 dari PRD, pencocokan varian, dan jaminan
  bahwa balasan tidak pernah mengklaim stok yang tidak diketahui.
- `tests/test_api.py` — acceptance criteria AC-01, AC-02, AC-03, AC-07, AC-09, AC-10,
  ditambah hak akses, validasi, catatan internal, dan audit log.

Masalah 2 — profitabilitas:

- `tests/test_profit.py` — laba dicocokkan dengan hitungan acuan yang ditulis manual di
  komentar, perilaku retur sebagian dan retur penuh, serta jaminan modal tidak dibebankan
  dua kali. Juga memastikan nol eksplisit berbeda dari data yang belum dicatat.
- `tests/test_profit_api.py` — hak akses (CS ditolak), konsistensi total per marketplace
  terhadap keseluruhan, penelusuran ringkasan ke rincian transaksi, penolakan transaksi
  ganda, dan impor CSV dengan baris bermasalah.

Pemetaan skenario studi kasus — Masalah 1:

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

Pemetaan skenario studi kasus — Masalah 2:

| Skenario                                   | Hasil yang diuji                                             |
| ------------------------------------------ | ------------------------------------------------------------ |
| Transaksi normal                            | Laba cocok dengan hitungan acuan manual                       |
| Retur sebagian (1 dari 2 unit)              | Penjualan dan modal berkurang sekali, tidak dua kali          |
| Retur penuh                                 | Rugi hanya sebesar voucher + ongkir, modal tidak dibebankan   |
| Modal produk belum dicatat                  | Laba `null`, margin `null`, ditandai belum lengkap            |
| Tarif potongan marketplace belum dicatat    | Laba `null`, bukan 0%                                         |
| Voucher ditulis 0 vs dikosongkan            | 0 dihitung sebagai nol; kosong ditandai belum lengkap         |
| Penjumlahan per marketplace                 | Totalnya sama persis dengan total keseluruhan                 |
| Ringkasan produk vs rincian transaksi       | Jumlah laba rincian sama dengan ringkasan                     |
| Transaksi diunggah dua kali                 | Ditolak, mencegah satu pesanan terhitung ganda                |
| Retur melebihi penjualan                    | Ditolak dengan pesan jelas                                    |
| CSV dengan baris bermasalah                 | Baris sah tetap tersimpan, baris gagal dilaporkan satu per satu |
| CS membuka laporan margin                   | Ditolak 403                                                   |

---

## 6. Data uji

Data sintetis di `backend/app/seed.py`: 4 pengguna, 12 percakapan, 4 produk
(9 varian), 4 FAQ, aturan pengiriman tiga marketplace, serta **16 transaksi** dengan
modal produk dan tarif potongan marketplace.

Kondisi yang sengaja dibuat tidak lengkap, untuk memperlihatkan perilaku eskalasi dan
penandaan data belum lengkap:

| Yang dikosongkan                    | Akibat yang terlihat                                      |
| ----------------------------------- | ---------------------------------------------------------- |
| Stok **Kurma Ajwa 250 g**           | Suggested reply minta verifikasi, tanpa klaim               |
| Stok **Kacang Arab 500 g** (90 jam) | Ditandai kedaluwarsa, minta konfirmasi                      |
| Aturan pengiriman **Lazada**        | Pertanyaan pengiriman dieskalasi                            |
| Modal **Cokelat Turki**             | Labanya tidak dihitung, ditandai belum lengkap (bukan nol)  |
| Tarif potongan **Lazada**           | Seluruh transaksi Lazada belum bisa dihitung labanya        |
| Voucher/ongkir dua transaksi        | Transaksi ditandai belum lengkap                            |

Dari 16 transaksi, 9 lengkap dan 7 belum lengkap, sehingga perilaku "data kosong bukan
nol" langsung terlihat saat demo tanpa perlu menyiapkan apa pun.

### Format CSV impor

```
external_id,marketplace_code,sku,order_date,quantity,gross_sales,voucher_seller,shipping_borne_by_seller,returned_quantity,returned_amount
SP-90001,shopee,AJW-1000,2026-11-01,2,400000,10000,15000,0,0
LZ-90002,lazada,KCA-500,2026-11-02,1,95000,,,0,0
```

Sel kosong pada kolom biaya berarti **belum diketahui**, dan dicatat sebagai belum
lengkap — bukan nol. Enam kolom pertama wajib ada.

### Rumus laba

```
penjualan bersih = gross_sales - returned_amount
komisi           = penjualan bersih x (komisi% + biaya layanan%)
modal            = modal per unit x (quantity - returned_quantity)
laba             = penjualan bersih - komisi - voucher - ongkir - modal
```

Nilai retur dikurangkan sekali dari penjualan. Barang yang diretur kembali ke stok,
sehingga modalnya ikut berkurang dan tidak dibebankan lagi. Komisi dihitung dari
penjualan bersih karena marketplace mengembalikan komisi atas pesanan yang diretur.

---

## 7. Susunan berkas

```
backend/
  app/
    main.py        FastAPI, CORS, startup
    db.py          engine SQLModel (PostgreSQL, SQLite untuk pengujian)
    models.py      tabel sesuai PRD bab 11
    schemas.py     validasi request/response
    auth.py        PBKDF2 password hashing, JWT, RBAC
    nlp.py         Masalah 1: classify() dan suggest() — fungsi murni, tanpa database
    profit.py      Masalah 2: perhitungan laba — fungsi murni, tanpa database
    services.py    jembatan database ↔ nlp, audit log
    routes.py      endpoint /api untuk inbox dan knowledge base
    profit_routes.py  endpoint /api/profit, termasuk impor CSV
    seed.py        data sintetis
  tests/           78 pengujian
frontend/
  src/app/
    login/                    halaman masuk
    (app)/layout.tsx          sidebar + topbar
    (app)/dashboard/          ringkasan operasional
    (app)/inbox/              unified inbox, detail, form tambah
    (app)/profitability/      laba per produk, marketplace, dan transaksi
    (app)/knowledge/          FAQ, produk/stok, pengiriman, eskalasi
  src/lib/api.ts              klien REST
  src/lib/ui.tsx              komponen dan token tampilan
docker-compose.yml
PRD.md             kebutuhan produk, acceptance criteria, model data
```

---

## 8. Teknologi

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

## 9. Yang belum dikerjakan

Disebutkan terbuka, bukan disembunyikan:

- Halaman manajemen pengguna dan form CRUD knowledge base belum ada; knowledge base
  masih tampil baca-saja dan diisi lewat `seed.py`.
- Belum ada migrasi database (Alembic); skema dibuat dengan `create_all` saat startup.
- Pengujian UI otomatis (Playwright) belum ada; alur UI diuji manual.
- Modal produk dan tarif potongan marketplace belum bisa disunting dari antarmuka;
  keduanya tampil baca-saja dan diisi lewat `seed.py` atau langsung ke database.
- Impor CSV belum mendukung pembaruan transaksi yang sudah ada; unggahan ulang untuk
  pesanan yang sama ditolak agar tidak terhitung dua kali.
- Prototipe diverifikasi end-to-end di atas SQLite. Jalur PostgreSQL disediakan lewat
  `docker-compose.yml` dengan kode yang sama (SQLModel), tetapi belum dijalankan penulis
  pada mesin uji karena Docker tidak aktif saat pengembangan.

---

## 10. Catatan penggunaan AI

Guidebook COMPARE 2026 meminta catatan alat bantu yang memuat nama alat, tujuan,
bagian yang digunakan, perubahan oleh tim, dan cara memeriksa hasilnya.

> **Diisi tim sebelum pengumpulan.** Tabel di bawah menyediakan kerangkanya; nama alat
> dan rincian pemeriksaan diisi sesuai yang benar-benar dilakukan tim.

| Yang disebutkan       | Penjelasan                                                                     |
| --------------------- | ------------------------------------------------------------------------------ |
| Alat dan kegunaan     | _(diisi tim)_                                                                   |
| Bagian yang digunakan | _(diisi tim)_                                                                   |
| Pemeriksaan tim       | _(diisi tim)_                                                                   |
| Hak dan biaya         | Tidak memakai layanan AI berbayar di dalam produk. Produk berjalan tanpa kuota pihak ketiga. |

Produk itu sendiri **tidak memanggil layanan AI apa pun saat berjalan**. Seluruh
klasifikasi dan perhitungan margin dilakukan oleh aturan di `backend/app/nlp.py` dan
`backend/app/profit.py`, sehingga hasilnya dapat ditelusuri baris per baris.

---

## 11. Privasi

Seluruh nama, nomor pesanan, dan angka pada data uji dibuat sendiri dan tidak mewakili
pelanggan, harga, atau transaksi nyata. ResponIn tidak menyimpan password, cookie, atau
token akun marketplace. Password pengguna disimpan sebagai hash PBKDF2, bukan teks biasa.
