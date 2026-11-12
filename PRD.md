# PRD — Scentra Manual Unified Inbox

Dokumen kebutuhan produk untuk **COMPARE 2026 — Business Case Hackathon**, studi kasus
"Layanan Pelanggan dan Profitabilitas Produk pada Usaha Oleh-Oleh Haji".

| | |
| --- | --- |
| Produk | Scentra Manual Unified Inbox |
| Pemilik usaha | Husin, Scentra Parfume (oleh-oleh haji dan herbal) |
| Versi dokumen | 1.0 |
| Status | Prototipe berjalan, lihat `README.md` |

---

## 1. Ringkasan

Scentra adalah workspace internal untuk tim Scentra Parfume. Satu aplikasi menangani dua
pekerjaan yang hari ini dikerjakan terpisah dan manual: membalas chat pembeli dari tiga
marketplace, dan menghitung apakah sebuah produk benar-benar untung.

Scentra tidak terhubung ke API marketplace mana pun. CS menyalin pesan pembeli ke
Scentra, lalu menyalin balasannya kembali ke Seller Center. Data penjualan masuk lewat
pengisian manual atau impor berkas CSV dari laporan marketplace.

Batasan itu datang dari kondisi nyata Husin: dia berjualan lewat Shopee, TikTok Shop,
dan Lazada tanpa akses API penjual, dan solusi yang mensyaratkan akses itu tidak akan
bisa dia pakai.

---

## 2. Masalah

### 2.1 Pertanyaan berulang menenggelamkan keluhan

Scentra Parfume menerima 500 sampai 700 pesanan per hari, kadang menembus 1000. Sebagian
besar chat berisi pertanyaan yang itu-itu saja: "Ready, Kak?", "Ada ukuran apa saja?",
"Bisa dikirim hari ini?". CS mengetik jawaban yang sama berulang kali, dan akibatnya
pembeli yang menyampaikan keluhan menunggu lebih lama daripada yang bertanya hal rutin.

Chat tersebar di tiga aplikasi penjual, sehingga tidak ada satu pun tempat yang
memperlihatkan seluruh antrean sekaligus.

### 2.2 Omzet besar belum tentu untung

Tiga marketplace memotong penjualan dengan cara dan besaran berbeda: komisi, biaya
layanan, voucher yang ditanggung penjual, ongkir yang ditanggung penjual, dan retur.
Husin melihat omzet naik, tetapi tidak tahu produk mana yang menyumbang laba dan mana
yang justru menggerus.

Yang hilang bukan datanya, melainkan tempat menggabungkannya. Angka penjualan ada di
laporan masing-masing marketplace, modal produk ada di catatan Husin, dan keduanya tidak
pernah bertemu.

---

## 3. Tujuan dan ukuran keberhasilan

| Tujuan | Ukuran |
| --- | --- |
| Keluhan tidak lagi mengantre di belakang pertanyaan rutin | Pesan berisi keluhan otomatis berprioritas tinggi dan dapat difilter tersendiri |
| CS berhenti mengetik ulang jawaban yang sama | Setiap pesan masuk disertai rekomendasi balasan yang tinggal disalin |
| Sistem tidak pernah menjanjikan yang tidak diketahui | Setiap rekomendasi yang berdiri di atas data kosong ditandai perlu verifikasi |
| Husin tahu produk mana yang untung | Laporan laba per produk dan per marketplace, dapat ditelusuri sampai transaksi |
| Angka tidak menyesatkan | Transaksi dengan data biaya belum lengkap dikeluarkan dari total, bukan dianggap nol |

Yang sengaja tidak dijadikan ukuran: kecepatan balas rata-rata dan tingkat kepuasan
pembeli. Keduanya terjadi di Seller Center, di luar jangkauan Scentra, sehingga tidak
bisa diukur jujur dari dalam aplikasi ini.

---

## 4. Pengguna dan peran

### 4.1 Customer service

Staf yang setiap hari membalas chat pembeli. Di data demo ada dua, Ayu dan Bima. Mereka
yang paling sering membuka Scentra, dan antarmuka inbox dirancang untuk mereka.

### 4.2 Pemilik usaha

Husin. Tidak ikut membalas chat. Dia membaca inbox untuk tahu apa yang sedang terjadi,
tetapi tidak mengubah isinya. Yang dia kelola adalah knowledge base, modal produk, tarif
marketplace, dan data penjualan, lalu membaca laporan profitabilitas.

### 4.3 Matriks hak akses

| Kemampuan | CS | Pemilik |
| --- | :-: | :-: |
| Melihat inbox dan detail percakapan | ya | ya, baca saja |
| Mencatat percakapan dan pesan baru | ya | tidak |
| Menyalin dan menyunting rekomendasi balasan | ya | tidak |
| Mengoreksi klasifikasi | ya | tidak |
| Mengubah status, prioritas, dan penugasan | ya | tidak |
| Menambah catatan internal dan catatan tindakan | ya | tidak |
| Membaca knowledge base | ya | ya |
| Membuka dashboard operasional | ya | ya |
| Membuka laporan profitabilitas | tidak | ya |
| Mencatat transaksi dan mengimpor CSV | tidak | ya |

Pembatasan ditegakkan di server, bukan dengan menyembunyikan menu. Permintaan langsung ke
endpoint yang tidak diizinkan dijawab 403.

---

## 5. Lingkup dan batasan

Termasuk lingkup:

- Pencatatan manual percakapan dari Shopee, TikTok Shop, dan Lazada ke satu antrean
- Klasifikasi pesan dan rekomendasi balasan berbasis aturan kata kunci
- Knowledge base berisi FAQ, katalog produk dan varian, stok, serta aturan pengiriman
- Pencatatan transaksi penjualan manual dan lewat impor CSV
- Laporan laba per produk, per marketplace, dan per periode
- Audit log untuk perubahan status, penugasan, koreksi klasifikasi, dan penyuntingan balasan

Di luar lingkup, dan alasannya:

| Yang tidak dibangun | Alasan |
| --- | --- |
| Integrasi API marketplace | Husin tidak punya aksesnya; syarat studi kasus |
| Pengiriman balasan dari dalam Scentra | Tanpa API, pengiriman tetap lewat Seller Center |
| Model bahasa atau layanan AI saat aplikasi berjalan | Keputusan harus bisa dijelaskan baris per baris dan tidak bergantung kuota pihak ketiga |
| Manajemen stok sebagai sumber kebenaran | Stok di Scentra adalah salinan catatan, bukan penggantinya |
| Pembukuan dan pajak | Laporan ini alat bantu keputusan produk, bukan laporan keuangan resmi |

---

## 6. Kebutuhan fungsional

### 6.1 Akses

**FR-01 Autentikasi.** Pengguna masuk dengan email dan password. Server membalas token
JWT berumur 12 jam. Password disimpan sebagai hash PBKDF2-HMAC-SHA256, tidak pernah
sebagai teks biasa.

**FR-02 Hak akses.** Setiap endpoint memeriksa peran pengguna sesuai matriks 4.4.

### 6.2 Masalah 1 — layanan pelanggan

**FR-03 Pencatatan percakapan.** CS membuat percakapan baru dengan mengisi marketplace,
nama pembeli, referensi pesanan atau chat, petunjuk produk bila ada, dan isi pesan yang
disalin persis dari Seller Center. Marketplace, nama, dan isi pesan wajib diisi.

**FR-04 Deteksi duplikasi.** Bila referensi yang dimasukkan sudah ada, sistem
memperingatkan sebelum menyimpan dan menawarkan menggabungkan pesan ke percakapan yang
sudah ada.

**FR-05 Klasifikasi otomatis.** Setiap pesan masuk diberi intent dan prioritas. Intent
yang dikenali: `stock_inquiry`, `product_inquiry`, `shipping_inquiry`, `order_inquiry`,
`complaint`, `return_refund`, `other`, `unknown`. Keluhan dan permintaan retur diperiksa
lebih dulu daripada intent lain.

**FR-06 Koreksi klasifikasi.** Pengguna dapat mengubah intent yang salah. Koreksi
disimpan beserta siapa yang mengoreksi, dan rekomendasi balasan disusun ulang.

**FR-07 Rekomendasi balasan.** Sistem menyusun balasan dari knowledge base dan
menampilkan sumber setiap pernyataan sebagai chip, misalnya `STOK · 1 kg · 24 pcs ·
3 jam lalu`. Teks dapat disunting sebelum disalin.

**FR-08 Penandaan perlu verifikasi.** Bila rekomendasi berdiri di atas data yang kosong
atau kedaluwarsa, balasan tidak membuat klaim dan percakapan ditandai perlu verifikasi
beserta alasannya.

**FR-09 Salin teks.** Tombol salin menyalin teks ke papan klip dan mencatat waktunya.
Tindakan ini tidak mengubah status percakapan.

**FR-10 Catatan internal.** Catatan yang hanya terlihat tim, terpisah dari pesan pembeli.

**FR-11 Catatan tindakan.** CS mencatat apa yang sudah dia lakukan, misalnya "balasan
dikirim lewat Seller Center". Catatan ini murni internal dan bukan bukti terkirim.

**FR-12 Status dan penugasan.** Status percakapan: New, Open, Assigned, Waiting for
Staff, Waiting for Customer, Resolved, Closed. Prioritas: high, normal, low. Penugasan ke
pengguna lain dilakukan sesama CS.

**FR-13 Filter dan pencarian.** Antrean dapat disaring menurut marketplace, status, dan
penandaan perlu verifikasi, serta dicari menurut nama, referensi, atau isi pesan.

**FR-14 Knowledge base.** Halaman baca untuk FAQ, produk dan varian beserta stok dan
waktu pembaruannya, aturan pengiriman per marketplace, dan aturan eskalasi.

**FR-15 Dashboard.** Ringkasan jumlah percakapan menurut marketplace, intent, dan status,
ditambah antrean prioritas tinggi.

**FR-16 Audit log.** Perubahan status, prioritas, penugasan, koreksi intent, penyuntingan
balasan, dan penyalinan tercatat beserta pelaku dan waktunya.

### 6.3 Masalah 2 — profitabilitas produk

**FR-17 Pencatatan transaksi.** Pemilik mencatat satu baris penjualan:
nomor pesanan, marketplace, SKU varian, tanggal, jumlah, penjualan kotor, voucher
penjual, ongkir yang ditanggung penjual, serta jumlah dan nilai retur.

**FR-18 Impor CSV.** Transaksi dapat diunggah dalam berkas CSV. Baris yang sah tetap
tersimpan walaupun ada baris lain yang gagal, dan setiap kegagalan dilaporkan per baris
dengan alasannya. Batas satu unggahan: 5.000 baris atau 2 MB.

**FR-19 Templat CSV.** Sistem menyediakan berkas contoh berisi kolom yang benar.

**FR-20 Laporan laba.** Laba dihitung per produk, per marketplace, dan untuk keseluruhan
periode terpilih, dengan filter periode dan marketplace.

**FR-21 Penandaan data belum lengkap.** Transaksi yang salah satu komponen biayanya belum
dicatat tidak dihitung labanya, ditandai belum lengkap beserta alasannya, dan dikeluarkan
dari total.

**FR-22 Penelusuran.** Setiap baris ringkasan dapat dibuka sampai ke daftar transaksi
penyusunnya, lengkap dengan rincian penjualan bersih, komisi, voucher, ongkir, dan modal.

**FR-23 Modal dan tarif.** Halaman baca untuk modal per varian dan tarif potongan per
marketplace, termasuk penandaan mana yang belum dicatat.

**FR-24 Penolakan transaksi ganda.** Kombinasi marketplace dan nomor pesanan bersifat
unik. Pesanan yang sudah tercatat ditolak agar tidak terhitung dua kali.

---

## 7. Aturan bisnis

**BR-01 Data kosong bukan nol.** Nilai yang belum dicatat disimpan sebagai `null` dan
ditampilkan sebagai tanda hubung, tidak pernah sebagai angka 0. Voucher yang memang
bernilai nol ditulis `0` dan diperlakukan sebagai nol. Keduanya harus dapat dibedakan.

**BR-02 Sistem tidak mengarang.** Rekomendasi balasan hanya boleh menyatakan fakta yang
ada di knowledge base. Stok yang belum tercatat tidak boleh dinyatakan tersedia maupun
habis.

**BR-03 Stok basi.** Catatan stok yang lebih tua dari 48 jam ditandai kedaluwarsa, dan
balasan meminta konfirmasi sebelum menjanjikan apa pun.

**BR-04 Nama bukan pengenal.** Dua pembeli bernama sama tidak pernah digabung. Pengenal
percakapan adalah referensi pesanan atau chat.

**BR-05 Scentra tidak mengirim apa pun.** Status di Scentra adalah pencatatan internal,
bukan bukti pesan terkirim di marketplace.

**BR-06 Retur dihitung sekali.** Nilai retur dikurangkan satu kali dari penjualan. Barang
yang diretur kembali ke stok, sehingga modalnya ikut berkurang dan tidak dibebankan lagi.

**BR-07 Uang sebagai bilangan bulat.** Nilai uang disimpan sebagai rupiah bulat dan tarif
potongan sebagai basis poin (1% = 100 bp), supaya tidak ada galat pembulatan desimal.

**BR-08 Komisi atas penjualan bersih.** Komisi dihitung dari penjualan setelah dikurangi
retur, karena marketplace mengembalikan komisi atas pesanan yang diretur.

Rumus laba:

```
penjualan bersih = gross_sales - returned_amount
komisi           = penjualan bersih x (komisi% + biaya layanan%)
modal            = modal per unit x (quantity - returned_quantity)
laba             = penjualan bersih - komisi - voucher - ongkir - modal
```

Margin dihitung hanya atas penjualan bersih dari transaksi yang lengkap, supaya data yang
belum lengkap tidak menurunkan persentase secara semu.

---

## 8. Alur layar

| Layar | Isi |
| --- | --- |
| Masuk | Email dan password, daftar akun demo |
| Dashboard | Hitungan per marketplace, intent, dan status, ditambah antrean prioritas tinggi |
| Unified Inbox | Daftar percakapan di kiri, detail di kanan, tombol tambah percakapan |
| Detail percakapan | Riwayat pesan, klasifikasi, rekomendasi balasan beserta sumber, status dan penugasan, catatan internal, riwayat aktivitas |
| Profitabilitas | Filter periode dan marketplace, lima kartu ringkasan, empat tab, tombol impor CSV |
| Knowledge Base | FAQ, produk dan varian beserta stok, aturan pengiriman, aturan eskalasi |

Empat tab pada layar profitabilitas: Per produk, Per marketplace, Rincian transaksi, dan
Modal & tarif. Mengklik nama produk membuka Rincian transaksi yang sudah tersaring ke SKU
produk itu.

Menu Profitabilitas tidak muncul bagi CS, dan membuka alamatnya langsung menampilkan
pesan akses terbatas.

---

## 9. Kebutuhan non-fungsional

### 9.1 Keamanan dan privasi data

Scentra tidak pernah menyimpan password, cookie, atau token akun marketplace. Password
pengguna disimpan sebagai hash PBKDF2-HMAC-SHA256 dengan salt acak. Token JWT
ditandatangani dengan kunci yang dibaca dari variabel lingkungan, bukan ditulis di kode.
Seluruh data demo bersifat sintetis dan tidak mewakili pelanggan, harga, atau transaksi
nyata. Pada deployment, aplikasi dilayani lewat HTTPS.

### 9.2 Kinerja

Daftar percakapan dan laporan laba harus terbuka di bawah dua detik pada data seukuran
satu bulan operasi. Perhitungan laba dilakukan di server dalam satu kali jalan atas
transaksi periode terpilih.

### 9.3 Keandalan

Kegagalan klasifikasi tidak boleh membatalkan penyimpanan pesan. Pesan tersimpan lebih
dulu, klasifikasi menyusul. Pada impor CSV, kegagalan satu baris tidak membatalkan baris
lain.

### 9.4 Ketertelusuran

Setiap angka pada ringkasan harus dapat ditelusuri sampai ke baris transaksi aslinya, dan
jumlah rincian harus sama persis dengan ringkasannya. Setiap pernyataan pada rekomendasi
balasan harus menyebut sumbernya.

### 9.5 Aksesibilitas

Status dan prioritas dibedakan dengan huruf, bukan warna saja. Elemen interaktif memiliki
penanda fokus yang terlihat, dan tombol pilihan memakai atribut `aria-pressed`. Tata letak
bekerja pada lebar layar ponsel.

---

## 10. Arsitektur

```
Seller Center marketplace          (di luar Scentra)
        │  pesan disalin manual
        ▼
Next.js (App Router) + Tailwind
        │  REST + JWT
        ▼
FastAPI
        │  classify() → intent + prioritas
        │  suggest()  → balasan + sumber
        │  compute()  → laba per transaksi
        ▼
PostgreSQL
```

`nlp.py` dan `profit.py` ditulis sebagai fungsi murni tanpa ketergantungan pada database,
sehingga logikanya dapat diuji tanpa menjalankan server.

---

## 11. Model data

| Tabel | Isi |
| --- | --- |
| `users` | Pengguna beserta peran dan hash password |
| `marketplaces` | Kode dan nama marketplace |
| `conversations` | Satu percakapan dengan satu pembeli, dikenali referensi |
| `messages` | Pesan pembeli, catatan internal, dan catatan tindakan |
| `classifications` | Intent, prioritas, versi aturan, dan penanda koreksi |
| `suggested_replies` | Teks rekomendasi, sumber, penanda verifikasi, waktu disalin |
| `faqs` | Pertanyaan, jawaban, dan kata kunci |
| `products` | Produk beserta aliasnya |
| `product_variants` | Varian dan SKU |
| `stock_records` | Jumlah stok dan waktu pembaruannya |
| `shipping_rules` | Aturan dan cutoff pengiriman per marketplace |
| `conversation_events` | Audit log perubahan |
| `product_costs` | Modal per varian |
| `marketplace_fees` | Komisi dan biaya layanan per marketplace, dalam basis poin |
| `transactions` | Baris penjualan beserta voucher, ongkir, dan retur |

Kolom biaya pada `transactions`, serta `unit_cost`, `commission_bp`, dan `service_fee_bp`,
boleh bernilai `null` yang berarti belum diketahui.

---

## 12. Acceptance criteria

### Masalah 1

| ID | Kriteria |
| --- | --- |
| AC-01 | Pesan baru tersimpan dengan marketplace, nama, referensi, dan isi; field wajib yang kosong ditolak 422 |
| AC-02 | Referensi yang sudah ada menghasilkan peringatan duplikasi dan pesan digabung; nama sama dengan referensi berbeda tetap dua percakapan |
| AC-03 | Pesan yang tidak dikenali tetap tersimpan dengan intent `unknown` |
| AC-04 | Setiap rekomendasi balasan menampilkan sumber pernyataannya |
| AC-05 | Stok yang belum tercatat tidak dinyatakan tersedia maupun habis, dan ditandai perlu verifikasi |
| AC-06 | Stok yang lebih tua dari 48 jam ditandai kedaluwarsa dan balasan meminta konfirmasi |
| AC-07 | Menyalin rekomendasi tidak mengubah status percakapan |
| AC-08 | Catatan tindakan tercatat sebagai catatan internal, tanpa klaim terkirim di marketplace |
| AC-09 | Pemilik ditolak 403 saat menulis ke percakapan; penugasan oleh CS tercatat di riwayat |
| AC-10 | Filter marketplace, status, dan perlu verifikasi mengembalikan hasil yang sesuai |

### Masalah 2

| ID | Kriteria |
| --- | --- |
| AC-11 | Laba transaksi sama dengan hitungan acuan menurut rumus pada bab 7 |
| AC-12 | Transaksi dengan modal atau tarif belum dicatat memiliki laba `null` dan margin `null` |
| AC-13 | Voucher bernilai `0` dihitung nol, voucher yang dikosongkan ditandai belum lengkap |
| AC-14 | Retur sebagian mengurangi penjualan dan modal masing-masing satu kali; retur penuh menghasilkan rugi sebesar voucher ditambah ongkir |
| AC-15 | Jumlah laba per marketplace sama persis dengan total keseluruhan |
| AC-16 | Jumlah laba rincian transaksi sama dengan ringkasan produknya |
| AC-17 | Pesanan yang sudah tercatat ditolak saat diunggah ulang |
| AC-18 | CS yang membuka laporan margin ditolak 403 |

Pemetaan kriteria ini ke berkas pengujian ada di `README.md` bab 5.

---

## 13. Rencana lanjutan

Yang disadari belum ada, dan akan dikerjakan bila produk diteruskan:

- Form penyuntingan knowledge base, modal produk, dan tarif marketplace dari antarmuka.
  Saat ini ketiganya baca-saja dan diisi lewat `seed.py`.
- Migrasi skema database dengan Alembic, menggantikan `create_all` saat startup.
- Pembaruan transaksi lewat impor ulang, yang sekarang ditolak demi mencegah hitung ganda.
- Pengujian antarmuka otomatis.
- Halaman manajemen pengguna.
