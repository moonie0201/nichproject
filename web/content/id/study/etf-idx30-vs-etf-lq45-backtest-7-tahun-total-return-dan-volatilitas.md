---
title: "ETF IDX30 vs ETF LQ45: Backtest 7 Tahun Total Return dan Volatilitas"
date: 2026-04-24
lastmod: 2026-04-24
draft: false
reviewed: true
analysis_confidence: "medium"
description: "ETF IDX30 vs ETF LQ45: backtest 7 tahun, total return, volatilitas, biaya, dan risiko untuk investor ritel Indonesia."
keywords: "ETF IDX30, ETF IDX30 vs ETF LQ45, backtest 7 tahun ETF Indonesia, total return dan volatilitas ETF, Premier ETF IDX30 vs Premier ETF LQ-45"
primary_keyword: "ETF IDX30"
schema: "HowTo"
toc: true
comments: true
cover:
    image: "/images/etf-idx30-vs-etf-lq45-backtest-7-tahun-total-return-dan-volatilitas/compound-growth.png"
    alt: "ETF IDX30 vs ETF LQ45: Backtest 7 Tahun Total Return dan Volatilitas"
    relative: false
tags:
  - "ETF IDX30"
  - "ETF LQ45"
  - "backtest 7 tahun"
  - "total return"
  - "volatilitas"
  - "pasar modal Indonesia"
  - "reksa dana indeks"
  - "alokasi aset jangka panjang"
  - "saham dividen"
  - "investasi pasif"
categories:
  - "Investasi"
  - "Keuangan Pribadi"
aliases:
  - /id/blog/etf-idx30-vs-etf-lq45-backtest-7-tahun-total-return-dan-volatilitas/
---
<div class="summary-box"><ul><li>Backtest 2018-2024 dari annual total return menghasilkan kumulatif sekitar -14.1% untuk XIIT dan +23.8% untuk R-LQ45X; CAGR-nya sekitar -2.2% vs 3.1%.</li><li>Pada snapshot 31 Juli 2024, return 3 tahun tercatat 16.33% untuk XIIT dan 21.94% untuk R-LQ45X; selisihnya tidak kecil, apalagi pada window 5 tahun yang bergeser ke -7.16% vs -0.72%.</li><li>Volatilitas 5 tahun dari Twelvedata berada di 15.79% untuk XIIT dan 13.94% untuk R-LQ45X; beda 1.85 poin persentase ini cukup untuk mengubah rasa perjalanan portofolio.</li><li>Harga terbaru pertengahan April 2026 menunjukkan XIIT di 513 dan R-LQ45X di 944; keduanya masih di bawah high 52 minggu, tetapi LQ45X lebih dekat ke puncak tahunan.</li><li>Mar 2020 tetap fase paling keras: XIIT -19.87% dan R-LQ45X -21.01% pada bulan terburuk, jadi dua ETF ini sama-sama tidak kebal saat likuiditas pasar tertekan.</li></ul></div>

## Kenapa simulasi Rp300 ribu/bulan tetap penting

<figure class="chart-figure"><img src="/images/etf-idx30-vs-etf-lq45-backtest-7-tahun-total-return-dan-volatilitas/compound-growth.png" alt="Simulasi bunga majemuk 20 tahun investasi bulanan" loading="lazy" style="max-width:100%;border-radius:8px;"><figcaption>Simulasi bunga majemuk 20 tahun investasi bulanan</figcaption></figure>

Grafik simulasi Rp300 ribu per bulan selama 20 tahun, dengan skenario 4%, 7%, dan 10%, memberi konteks yang sering dilupakan saat orang sibuk membandingkan ETF hanya dari nama indeks. Selisih return tahunan yang terlihat kecil di satu atau dua tahun bisa membesar setelah 10-20 tahun. Pada produk berbasis indeks, biaya, distribusi dividen, dan disiplin rebalancing biasanya lebih berpengaruh daripada narasi merek indeks yang terdengar lebih meyakinkan.

Di titik ini, backtest 7 tahun menjadi berguna karena memperlihatkan apakah IDX30 benar-benar lebih efisien daripada LQ45, atau justru sebaliknya. Data publik yang tersedia justru memberi jawaban yang tidak terlalu nyaman untuk konsensus pasar.

### Selisih kecil di biaya bisa jadi besar di waktu panjang

Premier ETF IDX30 dan Premier ETF LQ-45 sama-sama membawa biaya pengelolaan maksimum 1.00% per tahun. Namun, biaya kustodian pada dokumen produk yang terbit 2024/2025 terlihat di level maksimum 0.20% untuk XIIT dan 0.15% untuk R-LQ45X. Angka ini tidak sendirian menentukan hasil, tetapi dalam horizon 7 tahun atau lebih, biaya yang tampak kecil tetap menekan hasil bersih.

## Backtest 7 tahun 2018-2024: siapa yang lebih tahan?

Untuk window 7 tahun ini, annual total return dipakai lalu dikompaun. Itu lebih jujur daripada hanya menempelkan satu angka return 5 tahun lalu memanggilnya backtest panjang. Hasilnya cukup jelas: R-LQ45X memulai periode dengan 2018 yang sangat kuat, lalu tetap bertahan lebih baik saat pasar Indonesia melemah di 2020 dan 2024.

<table>
<thead>
<tr><th>Aspek</th><th>XIIT / IDX30</th><th>R-LQ45X / LQ45</th></tr>
</thead>
<tbody>
<tr><td>Annual total return 2018-2024</td><td>-14.1% kumulatif</td><td>+23.8% kumulatif</td></tr>
<tr><td>CAGR 2018-2024</td><td>-2.2%</td><td>3.1%</td></tr>
<tr><td>Return 2024</td><td>-9.0%</td><td>-10.52%</td></tr>
<tr><td>Return 2023</td><td>3.5%</td><td>5.24%</td></tr>
<tr><td>Return 2022</td><td>1.1%</td><td>3.00%</td></tr>
<tr><td>Return 2021</td><td>1.0%</td><td>3.09%</td></tr>
<tr><td>Return 2020</td><td>-6.4%</td><td>-5.67%</td></tr>
<tr><td>Return 2019</td><td>1.8%</td><td>0.67%</td></tr>
<tr><td>Return 2018</td><td>-6.3%</td><td>30.33%</td></tr>
</tbody>
</table>

Catatan metodologis: 7Y kumulatif dihitung dari compounding annual total returns 2018-2024. Itu berarti angka ini adalah inferensi dari data tahunan publik, bukan klaim hasil backtest harian penuh. Untuk volatilitas, bagian berikut memakai standard deviation 5 tahun dari Twelvedata sebagai proxy harian yang lebih dekat ke perilaku pasar.

Poin yang paling menonjol ada di 2018. R-LQ45X mencetak 30.33% pada tahun itu, sementara XIIT justru -6.3%. Itu membuat basis compounding LQ45X jauh lebih tinggi. Setelah itu, gap tidak sepenuhnya hilang. Pada 2020, keduanya terpukul. Pada 2021-2023, LQ45X kembali unggul. Pada 2024, keduanya merah, tetapi XIIT masih sedikit lebih baik di -9.0% dibanding -10.52%.

Data mendukung bacaan bahwa LQ45 bukan sekadar versi lebih luas yang pasti lebih encer. Berbeda dari konsensus pasar yang sering menilai IDX30 sebagai pilihan paling "elite", window 2018-2024 justru menunjukkan LQ45X menang di total return dan tetap lebih rapat dalam volatilitas.

<aside class="scenario-box">
  <div class="scenario-header">💡 Skenario Hipotetis: Pak Budi pada strategi akumulasi ETF bulanan</div>

  <div class="scenario-body">
    <p><strong>Pengaturan</strong>: Pak Budi adalah persona hipotetis berusia 34 tahun, IT consultant freelance di Jakarta Selatan, mulai 2020, memakai Mirae Asset Sekuritas + Stockbit, dengan akun ritel reguler. Alokasi bulanan Rp5.000.000 dipakai untuk membeli ETF secara bertahap.</p>
    <p>Dengan harga snapshot pertengahan April 2026, Rp5.000.000 kira-kira setara 9.746 unit XIIT pada 513 per unit, atau sekitar 5.296 unit R-LQ45X pada 944 per unit, sebelum spread dan komisi broker. Pada akun reguler, dividen tunai juga terkena PPh 10%, sehingga total return bersih akan sedikit di bawah angka bruto.</p>
    <p>Jika start date bergeser ke Maret 2020, hasil akhir bisa berubah tajam karena dua ETF sama-sama mengalami drawdown dua digit pada fase Covid; XIIT sempat -19.87% di bulan terburuk, sementara R-LQ45X -21.01%.</p>
  </div>

  <div class="scenario-footnote">Pak Budi adalah persona hipotetis untuk mengkonkretkan data. Bukan orang nyata, bukan transaksi nyata.</div>

</aside>

## Volatilitas: yang menang bukan selalu yang paling ramping

Kalau hanya melihat jumlah konstituen, LQ45 tampak lebih berantakan karena berisi 45 saham. Namun data volatilitas tidak mendukung tebakan sederhana itu. Twelvedata mencatat standard deviation 5 tahun di 15.79% untuk XIIT dan 13.94% untuk R-LQ45X. Selisih 1.85 poin persentase ini cukup berarti, terutama untuk investor ritel yang menatap portofolio tiap hari.

Snapshot harga juga memberi petunjuk yang searah. Pada April 2026, XIIT berada di 513 dengan rentang 52 minggu 444-635. Itu berarti posisinya sekitar 19.2% di bawah puncak tahunan. R-LQ45X berada di 944 dengan rentang 782-1100, atau sekitar 14.2% di bawah puncak tahunan. LQ45X masih lebih dekat ke high, yang biasanya dibaca sebagai momentum yang sedikit lebih kuat.

Namun, jangan dibaca terlalu lurus. XIIT justru punya 1-year return 13.56% pada data April 2026, sementara R-LQ45X sekitar 7.76% pada data pasar terbaru yang tersedia. Jadi momentum jangka pendek berpihak ke XIIT, sedangkan peta 7 tahun masih berpihak ke LQ45X. Dua hal itu bisa benar sekaligus.

### Komposisi sektor ikut menjelaskan beda perilaku

Fakta penting lain ada di komposisi. Pada factsheet XIIT 31 Juli 2024, sektor keuangan mencapai 52.82%, jauh di atas bobot keuangan pada R-LQ45X yang tercatat 29.44% pada data komposisi terbaru. R-LQ45X juga membawa porsi consumer defensive 20.89% dan consumer cyclical 12.34%, yang cenderung meredam satu sisi siklus bank. Secara sederhana, LQ45X lebih "campuran"; XIIT lebih condong ke bank dan financials.

Inilah alasan mengapa indeks yang terlihat lebih selektif tidak otomatis lebih stabil. Saat sektor keuangan melemah, konsentrasi tinggi justru bisa memperbesar guncangan. Saat sektor keuangan pulih, efeknya juga bisa lebih cepat terasa. Analisis ini bisa meleset bila rezim pasar bergeser ke fase yang lebih pro-financials dan pro-liquidity. Dalam skenario itu, XIIT punya peluang mengejar lebih cepat daripada yang dibaca oleh data 2018-2024.

## Sentimen berita dan risiko yang sering diabaikan

Berita pasar terbaru per 22 April 2026 menunjukkan BEI menyesuaikan kriteria evaluasi konstituen IDX30, LQ45, dan IDX80. Ini bukan detail kosmetik. Revisi metodologi bisa mengubah siapa yang masuk indeks, bagaimana bobot berubah, dan seberapa besar turnover saat rebalancing. Untuk ETF indeks lokal, itu berarti tracking cost dan distribusi performa bisa ikut bergerak.

Di sisi lain, data dividen menunjukkan kedua ETF tidak kosong total. XIIT tercatat membayar dividen pada 2020, 2021, 2022, dan 2024; R-LQ45X juga membayar dividen pada 2020, 2021, 2022, dan 2023. Karena akun ritel reguler mengenakan PPh dividen 10%, angka total return bruto di layar tetap harus dibaca sebagai angka sebelum pajak dividen. Di sinilah investor sering terkecoh: return yang terlihat rapi di tabel belum tentu sama dengan uang bersih yang diterima.

Efek lain yang jarang dibahas adalah turnover indeks. LQ45 lebih lebar, jadi kadang dianggap lebih tahan terhadap perubahan konstituen. Itu tidak sepenuhnya benar. Rotasi nama besar, penurunan likuiditas beberapa emiten, dan penyesuaian bobot dapat menimbulkan tracking drag. Sisi ini sering lebih penting daripada narasi "30 saham lebih eksklusif" versus "45 saham lebih diversifikasi".

### Skenario di mana bacaan ini bisa salah

Jika 2026-2028 berubah menjadi rezim rally yang dipimpin bank, broker, dan saham-saham likuid besar, XIIT bisa saja memperkecil bahkan membalik gap karena bobot sektoralnya sangat condong ke keuangan. Jika pada saat yang sama rebalancing BEI membuat LQ45X kehilangan beberapa nama kuat atau menambah nama yang kurang efisien, keunggulan historis LQ45X tidak otomatis berlanjut. Itu alasan kenapa angka 2018-2024 layak dibaca sebagai peta masa lalu, bukan jaminan lintasan berikutnya.

## Pertanyaan yang Sering Ditanyakan

### ETF IDX30 dan ETF LQ45 mana yang unggul dalam backtest 7 tahun?

Untuk window 2018-2024, R-LQ45X unggul dengan kumulatif sekitar +23.8% dan CAGR sekitar 3.1%, sedangkan XIIT berada di sekitar -14.1% kumulatif dan -2.2% CAGR. Keunggulan LQ45X terutama datang dari 2018 yang sangat kuat, lalu tetap bertahan di 2021-2023.

### Kenapa LQ45X bisa lebih baik meski indeksnya lebih besar?

Karena jumlah saham yang lebih banyak tidak otomatis berarti hasil lebih baik. Komposisi sektor, bobot bank, consumer defensive, dan nama-nama dengan kualitas likuiditas tertentu bisa membuat LQ45X lebih stabil pada window tertentu. Pada 2018-2024, itu terlihat lebih kuat daripada bacaan sederhana bahwa IDX30 lebih "elite".

### Apakah volatilitas XIIT lebih tinggi?

Ya, pada data Twelvedata 5 tahun, standard deviation XIIT tercatat 15.79% dibanding 13.94% untuk R-LQ45X. Selisihnya tidak ekstrem, tetapi cukup untuk mengubah rasa drawdown dan pemulihan portofolio.

### Apakah dividen membuat perbedaan besar?

Ya, terutama untuk investor ritel reguler karena dividen tunai terkena PPh 10%. XIIT dan R-LQ45X sama-sama membagikan dividen pada beberapa tahun, sehingga total return bruto dan hasil bersih setelah pajak tidak identik. Pada horizon panjang, efek pajak dan jadwal distribusi ikut menumpuk.

### Kapan analisis ini paling mungkin meleset?

Analisis ini bisa meleset jika periode berikutnya didominasi reli sektor finansial dan saham-saham likuid besar di IDX30, atau jika perubahan metodologi BEI membuat komposisi LQ45X kurang efisien. Dalam rezim seperti itu, hasil historis 2018-2024 bisa kehilangan daya prediksi.

**Sumber data**: [Twelve Data XIIT performance](https://twelvedata.com/markets/986836/mutual-fund/idx/xiit/performance), [Twelve Data XIIT risk](https://twelvedata.com/markets/986836/mutual-fund/idx/xiit/risk), [Twelve Data R-LQ45X risk](https://twelvedata.com/markets/105578/mutual-fund/idx/r.lq45x/risk), [Investing.com LQ45X](https://www.investing.com/etfs/premier-lq-45), [Factsheet XIIT 31 Jul 2024](https://media.bareksa.com/uploads/file_doc/2024/08/ABAXK30_factsheet.pdf), [Factsheet LQ45X 31 Jul 2024](https://media.bareksa.com/uploads/file_doc/2024/08/ABAXK45_factsheet.pdf).

<div class="disclaimer" style="font-size:0.85em;color:#666;border-top:1px solid #eee;padding-top:1em;margin-top:2em;">Konten ini dibagikan untuk informasi berdasarkan pengalaman pribadi dan data publik, bukan saran investasi atau rekomendasi membeli/menjual produk keuangan. Semua keputusan dan risiko adalah milik Anda.</div>

> Artikel ini hanya untuk tujuan informasi dan bukan merupakan saran investasi.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "Article",
  "headline": "ETF IDX30 vs ETF LQ45: Backtest 7 Tahun Total Return dan Volatilitas",
  "description": "ETF IDX30 vs ETF LQ45: backtest 7 tahun, total return, volatilitas, biaya, dan risiko untuk investor ritel Indonesia.",
  "datePublished": "2026-04-24",
  "dateModified": "2026-04-24",
  "author": {
    "@type": "Organization",
    "name": "InvestIQs Research",
    "url": "https://investiqs.net/id/about/"
  },
  "publisher": {
    "@type": "Organization",
    "name": "InvestIQs",
    "url": "https://investiqs.net/"
  },
  "mainEntityOfPage": {
    "@type": "WebPage",
    "@id": "https://investiqs.net/id/blog/etf-idx30-vs-etf-lq45-backtest-7-tahun-total-return-dan-volatilitas/"
  },
  "image": "https://investiqs.net/images/etf-idx30-vs-etf-lq45-backtest-7-tahun-total-return-dan-volatilitas/compound-growth.png"
}
</script>

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "FAQPage",
  "mainEntity": [
    {
      "@type": "Question",
      "name": "ETF IDX30 atau ETF LQ45 mana yang unggul dalam backtest 7 tahun?",
      "acceptedAnswer": {
        "@type": "Answer",
        "text": "Untuk window 2018-2024, R-LQ45X unggul dengan kumulatif sekitar +23.8% dan CAGR sekitar 3.1%, sementara XIIT sekitar -14.1% kumulatif dan -2.2% CAGR."
      }
    },
    {
      "@type": "Question",
      "name": "Apakah ETF LQ45 selalu lebih stabil daripada ETF IDX30?",
      "acceptedAnswer": {
        "@type": "Answer",
        "text": "Tidak selalu. Pada data 5 tahun, standard deviation R-LQ45X sekitar 13.94%, lebih rendah daripada XIIT sekitar 15.79%, tetapi hasil itu tetap bergantung pada rezim sektor dan tanggal mulai."
      }
    },
    {
      "@type": "Question",
      "name": "Mengapa hasil 7 tahun bisa berbeda dari 1 tahun terakhir?",
      "acceptedAnswer": {
        "@type": "Answer",
        "text": "Karena total return 7 tahun memasukkan tahun ekstrem seperti 2018 dan 2020, sedangkan 1 tahun terakhir hanya menangkap fase pasar yang lebih pendek. Momentum jangka pendek dan akumulasi panjang sering memberi bacaan berbeda."
      }
    },
    {
      "@type": "Question",
      "name": "Apakah dividen sudah masuk dalam analisis total return?",
      "acceptedAnswer": {
        "@type": "Answer",
        "text": "Ya, angka total return yang dipakai mengacu pada total return tahunan yang sudah memasukkan distribusi dividen, tetapi hasil bersih investor ritel reguler masih bisa turun karena PPh dividen 10%."
      }
    },
    {
      "@type": "Question",
      "name": "Di mana analisis ini bisa salah?",
      "acceptedAnswer": {
        "@type": "Answer",
        "text": "Jika 2026-2028 dipimpin reli sektor finansial dan nama-nama likuid besar di IDX30, XIIT bisa mengejar atau menyalip LQ45X. Perubahan kriteria BEI juga bisa mengubah komposisi dan biaya tracking."
      }
    }
  ]
}
</script>
