---
title: "Tentang — InvestIQs Research"
url: "/id/about/"
draft: false
reviewed: true
ShowToc: false
---

## InvestIQs Research

Platform riset berbasis data yang mencakup **ETF AS · ETF Indonesia · aset dividen · alokasi aset jangka panjang**. Setiap artikel memadukan data pasar publik dengan analisis berbantuan AI dan melewati verifikasi dua tahap sebelum dipublikasikan.

---

## Metodologi

1. **Verifikasi silang data real-time**
   - Refresh cache yfinance tiap hari 08:00 KST.
   - Yield dividen dihitung langsung dari `Ticker.dividends` dan dicocokkan dengan yfinance.info; jika selisih >30% diambil nilai konservatif.
   - Penolakan otomatis untuk outlier (P/E negatif, yield >15%).

2. **Analisis AI multi-agen**
   - ai-hedge-fund dengan 5 agen: Perspektif Warren Buffett / Teknikal / Fundamental / Sentimen Berita / Risiko.
   - Hanya sebagai referensi, bukan kesimpulan tunggal.

3. **Perbandingan Peer ETF**
   - Minimal satu peer dibandingkan pada expense ratio, dividen, atau total return.

4. **Contrarian angle + Skenario sanggahan**
   - Minimal satu sudut pandang berbeda dari konsensus pasar.
   - Minimal satu skenario di mana tesis bisa meleset.

5. **Verifikasi dua tahap**
   - Tahap 1 (aturan): panjang, tabel perbandingan, frasa terlarang, data sumber.
   - Tahap 2 (Gemini semantik): halusinasi, kontradiksi internal, risiko kepatuhan.

---

## Sumber Data

| Item | Sumber |
|------|--------|
| Harga, return, dividen | yfinance (Yahoo Finance API) |
| Perspektif AI | ai-hedge-fund multi-agen (Gemini 2.0 Flash) |
| Penulisan & verifikasi | Codex + Gemini |

---

## Prinsip Editorial

- **Informasi, bukan nasihat**: Semua konten adalah catatan riset berbasis data publik.
- **Kesadaran regulasi**: Tidak menggunakan perintah kategoris ("harus beli", "pasti naik").
- **Transparansi**: Bantuan AI diungkapkan via banner + disclaimer pada setiap artikel.
- **Publikasi harian**: Otomatis 06–08 KST dalam lima bahasa.

---

## Disclaimer

Seluruh konten adalah riset edukatif berdasarkan data yfinance publik dan analisis AI. Ini bukan nasihat investasi, bukan ajakan membeli/menjual efek. Keputusan dan risiko adalah milik Anda.
