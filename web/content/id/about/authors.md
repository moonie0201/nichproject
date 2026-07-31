---
title: "Proses Produksi dan Verifikasi Konten"
description: "Konten InvestIQs dibuat dengan alur editorial berbantuan AI, lalu melalui validasi berbasis aturan dan pencocokan dengan data publik. Kami mengungkap prosesnya beserta batasannya secara terbuka."
date: 2026-05-26
lastmod: 2026-07-31
draft: false
layout: "about"
ai_generated: true
human_reviewed: false
---

## Siapa yang menerbitkan situs ini

InvestIQs diterbitkan oleh **tim editorial InvestIQs** — sebuah organisasi, bukan analis perorangan. Kami tidak mengklaim ada analis bernama di balik setiap artikel, karena itu tidak benar. Halaman ini menjelaskan bagaimana konten dibuat, apa yang diperiksa, dan apa yang tidak.

## Bagaimana konten dibuat (transparansi)

Seluruh artikel analisis, ringkasan pasar, dan naskah video di InvestIQs **dibuat dengan alur editorial berbantuan AI menggunakan model bahasa besar (LLM)**. Bukan ditulis baris demi baris oleh analis manusia. Kami menyatakannya secara eksplisit alih-alih menyiratkan kepenulisan manusia.

### Model yang digunakan
- **Isi artikel**: Anthropic Claude (Haiku 4.5 / Sonnet 4.6)
- **Terjemahan dan lokalisasi**: Google Gemini, fallback OpenRouter
- **Bantuan pemeriksaan fakta**: Gemini 3.1 Pro Preview

Field `ai_models` pada front matter setiap artikel mencatat ID model yang benar-benar dipakai.

## Proses verifikasi

Peninjau manusia tidak membaca setiap artikel satu per satu. Sebagai gantinya, langkah otomatis berikut dijalankan:

1. **Kutipan data publik**: Angka hanya diambil dari sumber publik — yfinance, dokumen keterbukaan regulator, dan materi resmi penerbit ETF.
2. **Validasi berbasis aturan**: Klaim berlebihan, kata terlarang, dan frasa bergaya "jaminan pokok" diblokir otomatis.
3. **Pemeriksaan keseimbangan skenario**: Artikel yang hanya memuat sisi positif ditolak; bagian risiko dan skenario penurunan wajib ada.
4. **Gerbang SEO dan struktur**: Penggunaan kata kunci, struktur H2, dan panjang meta description diperiksa otomatis.

**Ini tidak menggantikan penilaian ahli.** AI bisa salah: kesalahan kutipan data, aturan pajak yang belum diperbarui, dan konteks pasar yang terlewat semuanya mungkin terjadi.

## Batasan dan penafian

- **Bukan saran investasi.** Semua konten bersifat informasi dan bukan rekomendasi membeli atau menjual efek apa pun.
- **Bukan saran pajak atau hukum.** Topik rekening berinsentif pajak dan pajak penghasilan dibahas secara umum. Konfirmasikan situasi Anda dengan profesional berlisensi.
- **Perbedaan waktu**: Angka mencerminkan saat penulisan (lihat field `data_fetched_at`). Pasar berubah cepat — verifikasi data terkini secara terpisah.
- **Laporkan kesalahan**: Jika Anda menemukan kesalahan fakta, angka, atau kutipan, beri tahu kami lewat [Kontak](/id/contact/). Kami verifikasi dan koreksi.

## Prinsip editorial

1. **Data lebih dulu**: Hanya data publik yang dapat diverifikasi yang dikutip.
2. **Dua sisi**: Manfaat dan risiko disajikan bersama; tulisan berat sebelah ditolak otomatis.
3. **Transparansi**: Penggunaan AI, model yang dipakai, dan waktu data diungkap pada front matter setiap artikel.

---

*Terakhir diperbarui: 2026-07-31*
