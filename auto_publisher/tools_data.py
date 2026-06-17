#!/usr/bin/env python3
"""
tools_data.py — InvestIQs 인터랙티브 도구(계산기) 데이터 갱신 + 페이지 양산.

기능:
  1. refresh  : yfinance로 티커 yield/expense/수익률 + 환율 fetch → web/data/tools/{tickers,fx}.json 갱신 (data_as_of 스탬프)
  2. generate : tickers.json + 언어별 에디토리얼 템플릿 → web/content/{lang}/tools/dividend-calculator/{ticker}.md 양산

AdSense 안전 원칙:
  - 실시간 시세 X. 주기 시드를 에디토리얼+계산기로 감쌈.
  - 티커마다 성격이 다른 차별화된 본문(배당성장/커버드콜/저보수 등) → thin/scaled content 회피.
  - 모든 페이지 data_as_of + 정보제공 고지.

사용:
  venv/bin/python3 -m auto_publisher.tools_data refresh
  venv/bin/python3 -m auto_publisher.tools_data generate
  venv/bin/python3 -m auto_publisher.tools_data all
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
WEB = ROOT / "web"
DATA_DIR = WEB / "data" / "tools"
CONTENT = WEB / "content"

LANGS = ["ko", "en", "ja", "vi", "id"]
GEN_TICKERS = ["SCHD", "JEPI", "VYM", "JEPQ", "QYLD"]

DATE = "2026-06-14"  # data_as_of; refresh 시 갱신

# ---- 티커별 에디토리얼 "앵글" (성격이 실제로 다름 → 차별화) ----
# 각 언어 × 티커: (intro_thesis, risk_para)
ANGLES = {
    "en": {
        "SCHD": (
            "SCHD (Schwab U.S. Dividend Equity ETF) tracks high-quality U.S. companies with a track record of sustained dividend growth, at a very low expense ratio. It is built around dividend *growth* and balance-sheet quality rather than the highest headline yield.",
            "Because SCHD screens for quality and growth, its yield is moderate. The trade-off is a focus on companies that can keep raising payouts, which historically behaves differently from high-distribution covered-call funds.",
        ),
        "JEPI": (
            "JEPI (JPMorgan Equity Premium Income ETF) generates income by combining a low-volatility U.S. equity portfolio with an options-overlay (equity-linked notes). The result is a high distribution and smoother ride, but capped upside in strong rallies.",
            "JEPI's high yield comes largely from option premium, not dividend growth. In strong bull markets it tends to lag the underlying index because the options overlay caps upside.",
        ),
        "VYM": (
            "VYM (Vanguard High Dividend Yield ETF) holds a broad, diversified basket of higher-yielding U.S. stocks at an extremely low cost. It favors breadth and low fees over concentration.",
            "VYM's diversification reduces single-stock risk, but its yield and growth sit between a pure growth fund and an income-overlay fund. Costs are among the lowest in the category.",
        ),
        "JEPQ": (
            "JEPQ (JPMorgan Nasdaq Equity Premium Income ETF) applies the same equity-premium-income approach as JEPI, but on a Nasdaq-100-style portfolio. Higher growth exposure means higher yield and higher volatility.",
            "JEPQ carries more volatility than JEPI due to its tech-heavy base, and it has a relatively short live history (launched 2022) — long-run figures should be treated as indicative, not proven.",
        ),
        "QYLD": (
            "QYLD (Global X NASDAQ 100 Covered Call ETF) writes covered calls on the entire Nasdaq-100, producing a very high distribution. It is an income-maximizing strategy that sacrifices most price appreciation.",
            "QYLD's distribution is high, but writing calls on the full index caps upside and limits long-term principal growth. Its expense ratio is also higher than broad-index ETFs.",
        ),
    },
    "ja": {
        "SCHD": (
            "SCHD(Schwab U.S. Dividend Equity ETF)は、増配を継続してきた質の高い米国企業に、非常に低い経費率で分散投資するETFです。表面利回りの高さよりも「増配」と財務の質を重視します。",
            "SCHDは質と増配でスクリーニングするため利回りは中程度です。その代わり、配当を増やし続けられる企業に焦点を当てており、高分配のカバードコール型とは値動きの性質が異なります。",
        ),
        "JEPI": (
            "JEPI(JPMorgan Equity Premium Income ETF)は、低ボラティリティの米国株ポートフォリオにオプション戦略(ELN)を組み合わせて分配金を生み出します。高い分配と値動きの安定が特徴ですが、上昇相場では上値が抑えられます。",
            "JEPIの高い利回りは主にオプションのプレミアム由来で、増配によるものではありません。強い上昇相場ではオプション戦略が上値を抑えるため、指数に劣後しやすい傾向があります。",
        ),
        "VYM": (
            "VYM(Vanguard High Dividend Yield ETF)は、利回りの高い米国株を幅広く分散して保有する超低コストETFです。集中よりも分散と低コストを重視します。",
            "VYMは分散により個別株リスクを抑えますが、利回りと成長は純粋な成長型とインカム型の中間に位置します。コストはカテゴリ内でも最低水準です。",
        ),
        "JEPQ": (
            "JEPQ(JPMorgan Nasdaq Equity Premium Income ETF)は、JEPIと同じ「エクイティ・プレミアム・インカム」戦略を、ナスダック100型のポートフォリオに適用したものです。成長エクスポージャーが高い分、利回りもボラティリティも高くなります。",
            "JEPQはハイテク比率が高いためJEPIより変動が大きく、設定が2022年と運用期間が短いため、長期の数値は参考値として扱う必要があります。",
        ),
        "QYLD": (
            "QYLD(Global X NASDAQ 100 Covered Call ETF)は、ナスダック100全体にカバードコールを設定し、非常に高い分配を生み出します。値上がり益の多くを犠牲にしてインカムを最大化する戦略です。",
            "QYLDの分配は高いものの、指数全体にコールを売るため上値が抑えられ、長期的な元本成長は限定的です。経費率も広範なインデックスETFより高めです。",
        ),
    },
    "ko": {
        "SCHD": (
            "SCHD(Schwab U.S. Dividend Equity ETF)는 배당을 꾸준히 늘려온 우량 미국 기업에 매우 낮은 보수로 분산 투자하는 ETF입니다. 표면 배당률보다 '배당 성장'과 재무 건전성을 중시합니다.",
            "SCHD는 품질과 성장으로 종목을 거르기 때문에 배당률은 중간 수준입니다. 대신 배당을 계속 늘릴 수 있는 기업에 집중하며, 고분배 커버드콜형과는 가격 움직임 성격이 다릅니다.",
        ),
        "JEPI": (
            "JEPI(JPMorgan Equity Premium Income ETF)는 저변동성 미국 주식 포트폴리오에 옵션 전략(ELN)을 결합해 분배금을 만듭니다. 높은 분배와 안정적 흐름이 특징이지만 강세장에서는 상단이 제한됩니다.",
            "JEPI의 높은 분배율은 대부분 옵션 프리미엄에서 나오며 배당 성장 때문이 아닙니다. 강한 상승장에서는 옵션 전략이 상단을 제한해 지수에 뒤처지는 경향이 있습니다.",
        ),
        "VYM": (
            "VYM(Vanguard High Dividend Yield ETF)은 배당률이 높은 미국 주식을 넓게 분산 보유하는 초저비용 ETF입니다. 집중보다 분산과 낮은 비용을 우선합니다.",
            "VYM은 분산으로 개별 종목 리스크를 줄이지만, 배당률과 성장은 순수 성장형과 인컴형의 중간에 위치합니다. 보수는 동종 최저 수준입니다.",
        ),
        "JEPQ": (
            "JEPQ(JPMorgan Nasdaq Equity Premium Income ETF)는 JEPI와 같은 '에쿼티 프리미엄 인컴' 전략을 나스닥100형 포트폴리오에 적용한 상품입니다. 성장 노출이 큰 만큼 분배율도 변동성도 높습니다.",
            "JEPQ는 기술주 비중이 높아 JEPI보다 변동이 크고, 2022년 설정으로 운용 기간이 짧아 장기 수치는 참고용으로만 봐야 합니다.",
        ),
        "QYLD": (
            "QYLD(Global X NASDAQ 100 Covered Call ETF)는 나스닥100 전체에 커버드콜을 매도해 매우 높은 분배를 만듭니다. 가격 상승분 대부분을 포기하고 인컴을 극대화하는 전략입니다.",
            "QYLD는 분배율이 높지만 지수 전체에 콜을 매도해 상단이 제한되고 장기 원금 성장이 제한적입니다. 보수도 광범위 인덱스 ETF보다 높습니다.",
        ),
    },
    "vi": {
        "SCHD": (
            "SCHD (Schwab U.S. Dividend Equity ETF) đầu tư phân tán vào các công ty Mỹ chất lượng có lịch sử tăng cổ tức bền vững, với mức phí rất thấp. Quỹ tập trung vào *tăng trưởng cổ tức* và chất lượng tài chính hơn là lợi suất danh nghĩa cao nhất.",
            "Vì SCHD sàng lọc theo chất lượng và tăng trưởng nên lợi suất ở mức vừa phải. Đổi lại, quỹ tập trung vào các công ty có thể tiếp tục tăng cổ tức, vận động khác với các quỹ covered-call phân phối cao.",
        ),
        "JEPI": (
            "JEPI (JPMorgan Equity Premium Income ETF) tạo thu nhập bằng cách kết hợp danh mục cổ phiếu Mỹ biến động thấp với chiến lược quyền chọn (ELN). Kết quả là mức phân phối cao và ổn định hơn, nhưng bị giới hạn lợi nhuận khi thị trường tăng mạnh.",
            "Lợi suất cao của JEPI chủ yếu đến từ phí quyền chọn chứ không phải tăng trưởng cổ tức. Trong thị trường tăng mạnh, quỹ thường tụt lại so với chỉ số vì chiến lược quyền chọn giới hạn lợi nhuận.",
        ),
        "VYM": (
            "VYM (Vanguard High Dividend Yield ETF) nắm giữ rổ cổ phiếu Mỹ lợi suất cao, đa dạng và chi phí cực thấp. Quỹ ưu tiên độ rộng và phí thấp hơn là tập trung.",
            "Sự đa dạng của VYM giảm rủi ro từng cổ phiếu, nhưng lợi suất và tăng trưởng nằm giữa quỹ tăng trưởng thuần và quỹ thu nhập. Chi phí thuộc nhóm thấp nhất.",
        ),
        "JEPQ": (
            "JEPQ (JPMorgan Nasdaq Equity Premium Income ETF) áp dụng cùng chiến lược thu nhập như JEPI nhưng trên danh mục kiểu Nasdaq-100. Mức độ tăng trưởng cao hơn đồng nghĩa lợi suất và biến động cao hơn.",
            "JEPQ biến động nhiều hơn JEPI do nền tảng nặng về công nghệ, và có lịch sử khá ngắn (ra mắt 2022) — số liệu dài hạn chỉ nên xem là tham khảo.",
        ),
        "QYLD": (
            "QYLD (Global X NASDAQ 100 Covered Call ETF) bán quyền chọn mua trên toàn bộ Nasdaq-100, tạo mức phân phối rất cao. Đây là chiến lược tối đa hóa thu nhập, đánh đổi phần lớn tăng giá.",
            "Phân phối của QYLD cao, nhưng bán quyền chọn trên toàn chỉ số giới hạn lợi nhuận và tăng trưởng vốn dài hạn. Phí cũng cao hơn các ETF chỉ số rộng.",
        ),
    },
    "id": {
        "SCHD": (
            "SCHD (Schwab U.S. Dividend Equity ETF) berinvestasi terdiversifikasi pada perusahaan AS berkualitas dengan rekam jejak pertumbuhan dividen, dengan rasio biaya sangat rendah. Fokusnya pada *pertumbuhan* dividen dan kualitas neraca, bukan imbal hasil tertinggi.",
            "Karena SCHD menyaring berdasarkan kualitas dan pertumbuhan, imbal hasilnya moderat. Sebagai gantinya, fokusnya pada perusahaan yang mampu terus menaikkan dividen, berperilaku berbeda dari dana covered-call berdistribusi tinggi.",
        ),
        "JEPI": (
            "JEPI (JPMorgan Equity Premium Income ETF) menghasilkan pendapatan dengan menggabungkan portofolio saham AS bervolatilitas rendah dengan strategi opsi (ELN). Hasilnya distribusi tinggi dan lebih stabil, tetapi kenaikan terbatas saat pasar reli kuat.",
            "Imbal hasil tinggi JEPI sebagian besar dari premi opsi, bukan pertumbuhan dividen. Di pasar bullish kuat, ia cenderung tertinggal dari indeks karena strategi opsi membatasi kenaikan.",
        ),
        "VYM": (
            "VYM (Vanguard High Dividend Yield ETF) memegang keranjang saham AS berimbal hasil tinggi yang luas dan terdiversifikasi dengan biaya sangat rendah. Mengutamakan keluasan dan biaya rendah dibanding konsentrasi.",
            "Diversifikasi VYM mengurangi risiko saham tunggal, tetapi imbal hasil dan pertumbuhannya berada di antara dana pertumbuhan murni dan dana pendapatan. Biayanya termasuk yang terendah.",
        ),
        "JEPQ": (
            "JEPQ (JPMorgan Nasdaq Equity Premium Income ETF) menerapkan strategi pendapatan yang sama seperti JEPI, tetapi pada portofolio bergaya Nasdaq-100. Eksposur pertumbuhan lebih tinggi berarti imbal hasil dan volatilitas lebih tinggi.",
            "JEPQ lebih bergejolak daripada JEPI karena basisnya berat teknologi, dan riwayatnya relatif pendek (diluncurkan 2022) — angka jangka panjang sebaiknya dianggap indikatif.",
        ),
        "QYLD": (
            "QYLD (Global X NASDAQ 100 Covered Call ETF) menjual covered call pada seluruh Nasdaq-100, menghasilkan distribusi sangat tinggi. Ini strategi memaksimalkan pendapatan dengan mengorbankan sebagian besar apresiasi harga.",
            "Distribusi QYLD tinggi, tetapi menjual call pada seluruh indeks membatasi kenaikan dan pertumbuhan pokok jangka panjang. Rasio biayanya juga lebih tinggi dari ETF indeks luas.",
        ),
    },
}

# 언어별 페이지 골격
TPL = {
    "en": {
        "title": "{tk} Dividend Calculator — Dividend Reinvestment Simulation",
        "desc": "Estimate {tk} ({name}) dividend income and balance over time from your investment, holding period, growth rate, and reinvestment. Currency display supported.",
        "h_intro": "See {tk}'s dividends in numbers",
        "h_yield": "Don't judge by yield alone",
        "p_yield_close": "Numbers are periodically updated reference values, not real-time. Actual dividends vary and are affected by taxes and FX.",
        "h_related": "Related tools & articles",
        "rel_other": "Compare other dividend ETFs:",
        "rel_study": "Learn the basics:",
        "study_url": "/en/study/",
        "study_label": "Study",
        "cta": "Every Friday we send a newsletter summarizing dividend ETF and U.S. market data.",
        "tags": ["{tk}", "dividend ETF", "dividend reinvestment", "DRIP"],
    },
    "ja": {
        "title": "{tk} 配当金 計算機 — 配当再投資シミュレーション",
        "desc": "{tk}({name})の配当利回りをもとに、投資額・保有年数・増配率・配当再投資から将来の配当金と評価額を試算できる計算機です。円建て表示にも対応。",
        "h_intro": "{tk} の配当金を数字で確認する",
        "h_yield": "配当利回りだけで判断しない",
        "p_yield_close": "数値は定期的に更新される参考値であり、リアルタイムではありません。実際の配当は変動し、税金や為替の影響も受けます。",
        "h_related": "関連ツール・記事",
        "rel_other": "他の配当ETFと比較する:",
        "rel_study": "投資の基礎を学ぶ:",
        "study_url": "/ja/study/",
        "study_label": "投資の学び",
        "cta": "毎週金曜、配当ETFと米国市場のデータをまとめたニュースレターをお届けします。",
        "tags": ["{tk}", "配当ETF", "新NISA", "配当再投資"],
    },
    "ko": {
        "title": "{tk} 배당금 계산기 — 배당 재투자 시뮬레이션",
        "desc": "{tk}({name}) 배당수익률을 기준으로 투자 원금·보유 기간·배당 성장률·재투자에 따른 미래 배당금과 평가액을 계산합니다. 원화 표시 지원.",
        "h_intro": "{tk}의 배당금을 숫자로 확인하세요",
        "h_yield": "배당률만 보고 판단하지 마세요",
        "p_yield_close": "수치는 주기적으로 갱신되는 참고값이며 실시간이 아닙니다. 실제 배당은 변동하며 세금·환율의 영향을 받습니다.",
        "h_related": "관련 도구·글",
        "rel_other": "다른 배당 ETF와 비교:",
        "rel_study": "투자 기초 배우기:",
        "study_url": "/ko/study/",
        "study_label": "투자공부",
        "cta": "매주 금요일, 배당 ETF와 미국 시장 데이터를 정리한 뉴스레터를 보내드립니다.",
        "tags": ["{tk}", "배당 ETF", "배당 재투자", "DRIP"],
    },
    "vi": {
        "title": "Máy tính cổ tức {tk} — Mô phỏng tái đầu tư cổ tức",
        "desc": "Ước tính thu nhập cổ tức và giá trị của {tk} ({name}) theo số tiền đầu tư, thời gian nắm giữ, tốc độ tăng và tái đầu tư. Hỗ trợ hiển thị theo tiền tệ.",
        "h_intro": "Xem cổ tức của {tk} bằng những con số",
        "h_yield": "Đừng chỉ nhìn vào lợi suất",
        "p_yield_close": "Các con số là giá trị tham khảo cập nhật định kỳ, không theo thời gian thực. Cổ tức thực tế thay đổi và chịu ảnh hưởng của thuế và tỷ giá.",
        "h_related": "Công cụ & bài viết liên quan",
        "rel_other": "So sánh các quỹ ETF cổ tức khác:",
        "rel_study": "Học kiến thức cơ bản:",
        "study_url": "/vi/study/",
        "study_label": "Học đầu tư",
        "cta": "Mỗi thứ Sáu, chúng tôi gửi bản tin tổng hợp dữ liệu quỹ ETF cổ tức và thị trường Mỹ.",
        "tags": ["{tk}", "ETF cổ tức", "tái đầu tư cổ tức", "DRIP"],
    },
    "id": {
        "title": "Kalkulator Dividen {tk} — Simulasi Reinvestasi Dividen",
        "desc": "Perkirakan pendapatan dividen dan nilai {tk} ({name}) dari jumlah investasi, jangka waktu, laju pertumbuhan, dan reinvestasi. Mendukung tampilan mata uang.",
        "h_intro": "Lihat dividen {tk} dalam angka",
        "h_yield": "Jangan menilai hanya dari imbal hasil",
        "p_yield_close": "Angka adalah nilai referensi yang diperbarui berkala, bukan real-time. Dividen aktual berubah dan dipengaruhi pajak serta kurs.",
        "h_related": "Alat & artikel terkait",
        "rel_other": "Bandingkan ETF dividen lain:",
        "rel_study": "Pelajari dasar-dasarnya:",
        "study_url": "/id/study/",
        "study_label": "Belajar Investasi",
        "cta": "Setiap Jumat kami mengirim buletin yang merangkum data ETF dividen dan pasar AS.",
        "tags": ["{tk}", "ETF dividen", "reinvestasi dividen", "DRIP"],
    },
}


def _load_tickers():
    with open(DATA_DIR / "tickers.json", encoding="utf-8") as f:
        return json.load(f)


def _related_links(lang, ticker, tpl):
    """ticker 본인을 제외한 다른 티커 2개 + study 링크."""
    others = [t for t in GEN_TICKERS if t != ticker][:2]
    lines = [f"- {tpl['rel_other']}"]
    for o in others:
        lines.append(f"  - [{o}](/{lang}/tools/dividend-calculator/{o.lower()}/)")
    lines.append(f"- {tpl['rel_study']} [{tpl['study_label']}]({tpl['study_url']})")
    return "\n".join(lines)


def generate():
    data = _load_tickers()
    tk_data = data["tickers"]
    as_of = data.get("data_as_of", DATE)
    count = 0
    for lang in LANGS:
        tpl = TPL[lang]
        for ticker in GEN_TICKERS:
            meta = tk_data.get(ticker, {})
            name = meta.get("name", ticker)
            intro, risk = ANGLES[lang][ticker]
            tags = ", ".join(f'"{t.format(tk=ticker)}"' for t in tpl["tags"])
            title = tpl["title"].format(tk=ticker, name=name)
            desc = tpl["desc"].format(tk=ticker, name=name)
            body = f"""---
title: "{title}"
description: "{desc}"
date: {as_of}T00:00:00+09:00
lastmod: {as_of}T00:00:00+09:00
draft: false
type: "tools"
tool: "dividend-calculator"
ticker: "{ticker}"
schema: "Article"
author: "InvestIQs Editorial"
tags: [{tags}]
data_as_of: "{as_of}"
disclaimer: true
---

## {tpl['h_intro'].format(tk=ticker)}

{intro}

## {tpl['h_yield']}

{risk}

{tpl['p_yield_close']}

## {tpl['h_related']}

{_related_links(lang, ticker, tpl)}

{tpl['cta']}
"""
            out = CONTENT / lang / "tools" / "dividend-calculator" / f"{ticker.lower()}.md"
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text(body, encoding="utf-8")
            count += 1
    print(f"generated {count} dividend-calculator pages ({len(LANGS)} langs x {len(GEN_TICKERS)} tickers)")


def refresh():
    """yfinance로 시드 갱신. 네트워크 필요."""
    import yfinance as yf
    import datetime
    today = datetime.date.today().isoformat()
    tickers = _load_tickers()
    for tk, meta in tickers["tickers"].items():
        try:
            info = yf.Ticker(tk).info
            y = info.get("dividendYield")
            er = info.get("annualReportExpenseRatio") or info.get("netExpenseRatio")
            px = info.get("regularMarketPrice") or info.get("previousClose")
            if y is not None:
                meta["yield_pct"] = round(float(y), 4)
            if er is not None:
                meta["expense_ratio_pct"] = round(float(er), 4)
            if px is not None:
                meta["price_usd"] = round(float(px), 2)
            print(f"  {tk}: yield={meta.get('yield_pct')} px={meta.get('price_usd')}")
        except Exception as e:
            print(f"  {tk}: refresh failed: {str(e)[:80]}")
    tickers["data_as_of"] = today
    (DATA_DIR / "tickers.json").write_text(
        json.dumps(tickers, ensure_ascii=False, indent=2), encoding="utf-8")
    # FX
    fx = json.loads((DATA_DIR / "fx.json").read_text(encoding="utf-8"))
    pairs = {"KRW": "KRW=X", "JPY": "JPY=X", "VND": "VND=X", "IDR": "IDR=X"}
    for cur, sym in pairs.items():
        try:
            h = yf.Ticker(sym).history(period="5d")["Close"].dropna()
            if len(h):
                fx["rates"][cur] = round(float(h.iloc[-1]), 4)
        except Exception as e:
            print(f"  fx {cur}: {str(e)[:60]}")
    fx["data_as_of"] = today
    (DATA_DIR / "fx.json").write_text(
        json.dumps(fx, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"refreshed seed data, data_as_of={today}")


COMPARE_PAIRS = [
    ("SCHD", "VYM"),
    ("SCHD", "JEPI"),
    ("JEPI", "JEPQ"),
    ("QYLD", "JEPQ"),
    ("VOO", "SPY"),
    ("SCHD", "VOO"),
]

COMPARE_DATE = "2026-06-14"

# Per-pair, per-lang editorial copy: (intro_para, outro_para)
COMPARE_ANGLES = {
    "en": {
        ("SCHD", "VYM"): (
            "SCHD and VYM are both U.S. large-cap dividend ETFs with very low costs and broad diversification. SCHD screens more tightly for dividend growth and quality, while VYM casts a wider net across higher-yielding stocks.",
            "Both ETFs favor financial stability and broad exposure. SCHD's stricter quality screen results in a smaller, more concentrated portfolio, whereas VYM holds over 400 stocks for maximum breadth.",
        ),
        ("SCHD", "JEPI"): (
            "SCHD and JEPI represent two distinct income approaches. SCHD pursues dividend growth through equity ownership; JEPI supplements equity income with an options overlay to deliver a higher monthly distribution.",
            "SCHD's income tends to grow over time as portfolio companies raise dividends. JEPI's payout is partially driven by options premium, which can fluctuate with market volatility — a different risk profile.",
        ),
        ("JEPI", "JEPQ"): (
            "JEPI and JEPQ share the same JPMorgan equity-premium-income strategy but differ in their equity base. JEPI uses a low-volatility U.S. stock portfolio; JEPQ applies the same overlay to Nasdaq-100-style holdings.",
            "JEPQ carries greater growth potential through its tech-heavy Nasdaq base but also higher volatility. JEPI's lower-volatility equity selection has historically produced a smoother return profile.",
        ),
        ("QYLD", "JEPQ"): (
            "Both QYLD and JEPQ are Nasdaq-linked covered-call funds, but with different coverage ratios. QYLD sells calls on 100% of its index exposure; JEPQ uses a selective options overlay that preserves more upside.",
            "QYLD's full covered-call approach maximizes current distributions but heavily limits price appreciation. JEPQ retains more equity upside due to partial options coverage and launched in 2022 — its long-term track record is still developing.",
        ),
        ("VOO", "SPY"): (
            "VOO and SPY both track the S&P 500 and hold virtually identical portfolios. The key practical difference is the expense ratio: VOO charges 0.03%, while SPY charges 0.0945%.",
            "For long-term investors, the cost difference compounds meaningfully over decades. SPY has higher average daily trading volume and tighter bid-ask spreads, which may matter more to active traders.",
        ),
        ("SCHD", "VOO"): (
            "SCHD and VOO represent income versus total-return orientations within U.S. large-cap equities. SCHD focuses on dividend-paying quality companies; VOO tracks the full S&P 500 with a much smaller yield but broader market coverage.",
            "SCHD's income is higher and more visible quarter to quarter. VOO's total return has historically included capital appreciation across all S&P 500 sectors, including high-growth technology names that SCHD underweights.",
        ),
    },
    "ja": {
        ("SCHD", "VYM"): (
            "SCHDとVYMは、どちらも超低コストで広く分散された米国大型配当ETFです。SCHDは配当成長と質でより厳格にスクリーニングし、VYMはより広い範囲の高配当株をカバーします。",
            "両ETFとも財務安定性と幅広い分散を重視します。SCHDの厳格な質スクリーニングにより保有銘柄数は少なくなりますが、VYMは400銘柄以上を保有してより幅広い分散を提供します。",
        ),
        ("SCHD", "JEPI"): (
            "SCHDとJEPIは2つの異なるインカムアプローチを代表しています。SCHDは株式保有を通じた配当成長を追求し、JEPIはオプション戦略を加えて高い月次分配を実現します。",
            "SCHDのインカムはポートフォリオ企業が増配するにつれ時間とともに成長する傾向があります。JEPIの分配金は一部オプションプレミアム由来のため、市場ボラティリティにより変動します。",
        ),
        ("JEPI", "JEPQ"): (
            "JEPIとJEPQはJPモルガンの同じエクイティ・プレミアム・インカム戦略を使いますが、株式基盤が異なります。JEPIは低ボラティリティの米国株ポートフォリオを使い、JEPQはナスダック100型の保有銘柄に同じオーバーレイを適用します。",
            "JEPQはナスダックのハイテク比率が高い分、成長ポテンシャルとボラティリティの両方が高くなります。JEPIの低ボラティリティ株選択は、歴史的により安定したリターン推移をもたらしています。",
        ),
        ("QYLD", "JEPQ"): (
            "QYLDとJEPQはどちらもナスダック連動のカバードコールファンドですが、カバー比率が異なります。QYLDは指数エクスポージャーの100%にコールを売り、JEPQはより選択的なオプションオーバーレイでより多くの上値を確保します。",
            "QYLDの全量カバードコール戦略は現在の分配を最大化しますが、値上がり益を大きく制限します。JEPQは部分的なオプションカバーでより多くの株式上値を保持し、2022年設定と運用期間も短いため長期実績はまだ発展途上です。",
        ),
        ("VOO", "SPY"): (
            "VOOとSPYはどちらもS&P500に連動しており、保有銘柄はほぼ同一です。実務上の主な違いは経費率で、VOOは0.03%、SPYは0.0945%です。",
            "長期投資家にとって、コスト差は数十年にわたって大きく複利的に積み重なります。SPYの日次売買高は高く、ビッドアスクスプレッドも狭いため、アクティブトレーダーにとってはより重要になる場合があります。",
        ),
        ("SCHD", "VOO"): (
            "SCHDとVOOは、米国大型株の中でインカム志向と総合リターン志向を代表しています。SCHDは配当を支払う質の高い企業に注目し、VOOはS&P500全体を追跡しますが利回りははるかに低くより広い市場カバレッジを持ちます。",
            "SCHDのインカムは四半期ごとにより高く目に見える形で受け取れます。VOOの総合リターンは歴史的に、SCHDが低ウェイトとするハイテク成長株を含むS&P500全セクターにわたるキャピタルゲインを含んでいます。",
        ),
    },
    "ko": {
        ("SCHD", "VYM"): (
            "SCHD와 VYM은 모두 초저비용으로 폭넓게 분산된 미국 대형주 배당 ETF입니다. SCHD는 배당 성장과 품질 기준으로 더 엄격히 종목을 걸러내고, VYM은 더 넓은 범위의 고배당 주식을 포괄합니다.",
            "두 ETF 모두 재무 안정성과 광범위한 분산을 중시합니다. SCHD는 엄격한 품질 스크리닝으로 보유 종목 수가 적지만, VYM은 400개 이상의 종목으로 최대한 넓은 분산을 제공합니다.",
        ),
        ("SCHD", "JEPI"): (
            "SCHD와 JEPI는 두 가지 서로 다른 인컴 접근법을 대표합니다. SCHD는 주식 보유를 통한 배당 성장을 추구하고, JEPI는 옵션 전략을 더해 높은 월 배당을 만들어냅니다.",
            "SCHD의 수입은 포트폴리오 기업이 증배하면서 시간이 지남에 따라 성장하는 경향이 있습니다. JEPI의 분배금은 일부 옵션 프리미엄에서 나오기 때문에 시장 변동성에 따라 달라질 수 있습니다.",
        ),
        ("JEPI", "JEPQ"): (
            "JEPI와 JEPQ는 JP모건의 동일한 에쿼티 프리미엄 인컴 전략을 사용하지만 주식 기반이 다릅니다. JEPI는 저변동성 미국 주식 포트폴리오를 사용하고, JEPQ는 같은 오버레이를 나스닥100형 보유 종목에 적용합니다.",
            "JEPQ는 나스닥의 기술주 비중이 높아 성장 잠재력과 변동성이 모두 큽니다. JEPI의 저변동성 종목 선택은 역사적으로 더 안정적인 수익 흐름을 만들어왔습니다.",
        ),
        ("QYLD", "JEPQ"): (
            "QYLD와 JEPQ는 모두 나스닥 연동 커버드콜 펀드이지만 커버 비율이 다릅니다. QYLD는 지수 노출의 100%에 콜을 매도하고, JEPQ는 더 선택적인 옵션 오버레이로 더 많은 상단을 보존합니다.",
            "QYLD의 전량 커버드콜 전략은 현재 분배를 극대화하지만 가격 상승을 크게 제한합니다. JEPQ는 부분적인 옵션 커버로 더 많은 주가 상승 여력을 유지하며, 2022년 설정으로 운용 기간이 짧아 장기 실적은 아직 형성 중입니다.",
        ),
        ("VOO", "SPY"): (
            "VOO와 SPY는 모두 S&P 500을 추종하며 보유 종목이 거의 동일합니다. 실질적인 주요 차이는 운용보수로, VOO는 0.03%, SPY는 0.0945%입니다.",
            "장기 투자자에게 비용 차이는 수십 년에 걸쳐 복리로 유의미하게 누적됩니다. SPY는 일평균 거래량이 더 많고 매수·매도 스프레드가 좁아 단기 매매에서는 더 유리할 수 있습니다.",
        ),
        ("SCHD", "VOO"): (
            "SCHD와 VOO는 미국 대형주 안에서 인컴 지향과 총수익 지향을 각각 대표합니다. SCHD는 배당을 지급하는 우량 기업에 집중하고, VOO는 S&P 500 전체를 추종하지만 배당수익률은 훨씬 낮고 시장 커버리지는 더 넓습니다.",
            "SCHD의 인컴은 분기마다 더 높고 눈에 보이는 형태로 지급됩니다. VOO의 총수익에는 역사적으로 SCHD가 낮게 편입한 고성장 기술주를 포함한 S&P 500 전 섹터의 자본 차익이 포함됩니다.",
        ),
    },
    "vi": {
        ("SCHD", "VYM"): (
            "SCHD và VYM đều là các ETF cổ tức vốn hóa lớn của Mỹ với chi phí rất thấp và đa dạng hóa rộng rãi. SCHD sàng lọc chặt chẽ hơn về tăng trưởng cổ tức và chất lượng, trong khi VYM bao phủ phạm vi rộng hơn các cổ phiếu có lợi suất cao.",
            "Cả hai ETF đều ưu tiên sự ổn định tài chính và đa dạng hóa rộng. Tiêu chí chất lượng chặt chẽ hơn của SCHD dẫn đến danh mục nhỏ hơn, trong khi VYM nắm giữ hơn 400 cổ phiếu để tối đa hóa độ rộng.",
        ),
        ("SCHD", "JEPI"): (
            "SCHD và JEPI đại diện cho hai phương pháp tạo thu nhập khác nhau. SCHD theo đuổi tăng trưởng cổ tức thông qua việc nắm giữ cổ phiếu; JEPI bổ sung thu nhập từ cổ phiếu bằng chiến lược quyền chọn để mang lại phân phối tháng cao hơn.",
            "Thu nhập của SCHD có xu hướng tăng theo thời gian khi các công ty trong danh mục tăng cổ tức. Khoản chi trả của JEPI một phần được thúc đẩy bởi phí quyền chọn, có thể biến động theo biến động thị trường.",
        ),
        ("JEPI", "JEPQ"): (
            "JEPI và JEPQ sử dụng cùng chiến lược thu nhập từ vốn cổ phần của JPMorgan nhưng khác nhau về danh mục cổ phiếu. JEPI sử dụng danh mục cổ phiếu Mỹ biến động thấp; JEPQ áp dụng overlay tương tự trên các cổ phiếu kiểu Nasdaq-100.",
            "JEPQ mang lại tiềm năng tăng trưởng lớn hơn qua nền tảng Nasdaq nhiều công nghệ nhưng cũng có biến động cao hơn. Việc lựa chọn cổ phiếu biến động thấp của JEPI theo lịch sử đã tạo ra hồ sơ lợi nhuận ổn định hơn.",
        ),
        ("QYLD", "JEPQ"): (
            "Cả QYLD và JEPQ đều là quỹ covered-call liên kết Nasdaq, nhưng với tỷ lệ bao phủ khác nhau. QYLD bán call trên 100% exposure chỉ số; JEPQ sử dụng overlay quyền chọn chọn lọc để giữ lại nhiều tiềm năng tăng hơn.",
            "Cách tiếp cận covered-call đầy đủ của QYLD tối đa hóa phân phối hiện tại nhưng hạn chế đáng kể mức tăng giá. JEPQ giữ lại nhiều tiềm năng tăng hơn nhờ bao phủ quyền chọn một phần và ra mắt năm 2022 — hồ sơ dài hạn vẫn đang được xây dựng.",
        ),
        ("VOO", "SPY"): (
            "VOO và SPY đều theo dõi S&P 500 và nắm giữ danh mục gần như giống nhau. Sự khác biệt thực tế chính là tỷ lệ chi phí: VOO tính 0.03%, trong khi SPY tính 0.0945%.",
            "Đối với nhà đầu tư dài hạn, sự khác biệt về chi phí tích lũy đáng kể qua nhiều thập kỷ. SPY có khối lượng giao dịch trung bình hàng ngày cao hơn và chênh lệch bid-ask hẹp hơn, điều này có thể quan trọng hơn đối với nhà giao dịch tích cực.",
        ),
        ("SCHD", "VOO"): (
            "SCHD và VOO đại diện cho định hướng thu nhập so với tổng lợi nhuận trong cổ phiếu vốn hóa lớn của Mỹ. SCHD tập trung vào các công ty chất lượng trả cổ tức; VOO theo dõi toàn bộ S&P 500 với lợi suất thấp hơn nhiều nhưng phạm vi thị trường rộng hơn.",
            "Thu nhập của SCHD cao hơn và rõ ràng hơn theo từng quý. Tổng lợi nhuận của VOO theo lịch sử bao gồm tăng giá vốn trên tất cả các lĩnh vực S&P 500, bao gồm các cổ phiếu công nghệ tăng trưởng cao mà SCHD đang thiếu tỷ trọng.",
        ),
    },
    "id": {
        ("SCHD", "VYM"): (
            "SCHD dan VYM keduanya adalah ETF dividen saham besar AS dengan biaya sangat rendah dan diversifikasi luas. SCHD menyaring lebih ketat untuk pertumbuhan dividen dan kualitas, sementara VYM mencakup lebih luas saham-saham berimbal hasil tinggi.",
            "Kedua ETF mengutamakan stabilitas keuangan dan eksposur luas. Penyaringan kualitas SCHD yang lebih ketat menghasilkan portofolio yang lebih kecil dan terkonsentrasi, sedangkan VYM memegang lebih dari 400 saham untuk keluasan maksimal.",
        ),
        ("SCHD", "JEPI"): (
            "SCHD dan JEPI mewakili dua pendekatan pendapatan yang berbeda. SCHD mengejar pertumbuhan dividen melalui kepemilikan saham; JEPI menambah pendapatan ekuitas dengan overlay opsi untuk memberikan distribusi bulanan yang lebih tinggi.",
            "Pendapatan SCHD cenderung tumbuh seiring waktu saat perusahaan portofolio menaikkan dividen. Pembayaran JEPI sebagian didorong oleh premi opsi, yang dapat berfluktuasi dengan volatilitas pasar.",
        ),
        ("JEPI", "JEPQ"): (
            "JEPI dan JEPQ berbagi strategi equity-premium-income JPMorgan yang sama tetapi berbeda dalam basis ekuitas mereka. JEPI menggunakan portofolio saham AS bervolatilitas rendah; JEPQ menerapkan overlay yang sama pada kepemilikan bergaya Nasdaq-100.",
            "JEPQ membawa potensi pertumbuhan lebih besar melalui basis Nasdaq yang berat teknologi tetapi juga volatilitas lebih tinggi. Pemilihan ekuitas bervolatilitas rendah JEPI secara historis menghasilkan profil return yang lebih mulus.",
        ),
        ("QYLD", "JEPQ"): (
            "QYLD dan JEPQ keduanya adalah dana covered-call terkait Nasdaq, tetapi dengan rasio cakupan berbeda. QYLD menjual call pada 100% eksposur indeksnya; JEPQ menggunakan overlay opsi selektif yang mempertahankan lebih banyak kenaikan.",
            "Pendekatan covered-call penuh QYLD memaksimalkan distribusi saat ini tetapi sangat membatasi apresiasi harga. JEPQ mempertahankan lebih banyak kenaikan ekuitas karena cakupan opsi sebagian dan diluncurkan pada 2022 — rekam jejak jangka panjangnya masih berkembang.",
        ),
        ("VOO", "SPY"): (
            "VOO dan SPY keduanya melacak S&P 500 dan memegang portofolio yang hampir identik. Perbedaan praktis utama adalah rasio biaya: VOO mengenakan 0,03%, sementara SPY mengenakan 0,0945%.",
            "Bagi investor jangka panjang, perbedaan biaya terkumulasi secara bermakna selama beberapa dekade. SPY memiliki volume perdagangan harian rata-rata lebih tinggi dan spread bid-ask lebih ketat, yang mungkin lebih penting bagi trader aktif.",
        ),
        ("SCHD", "VOO"): (
            "SCHD dan VOO mewakili orientasi pendapatan versus total return dalam saham besar AS. SCHD berfokus pada perusahaan berkualitas yang membayar dividen; VOO melacak seluruh S&P 500 dengan imbal hasil yang jauh lebih kecil tetapi cakupan pasar yang lebih luas.",
            "Pendapatan SCHD lebih tinggi dan lebih terlihat dari kuartal ke kuartal. Total return VOO secara historis mencakup apresiasi modal di semua sektor S&P 500, termasuk saham teknologi pertumbuhan tinggi yang SCHD kekurangan bobot.",
        ),
    },
}

COMPARE_TPL = {
    "en": {
        "title": "{a} vs {b} — ETF Comparison",
        "desc": "Side-by-side comparison of {a} and {b}: dividend yield, expense ratio, 1-year and 5-year returns, and risk notes. Estimate annual income from any investment amount.",
        "h_compare": "{a} vs {b}: Key Differences",
        "h_income": "Estimate Your Income",
        "p_income": "Enter an investment amount above to compare estimated annual and monthly income from {a} and {b} side by side.",
        "h_related": "Related tools",
        "cta": "Every Friday we send a newsletter summarizing dividend ETF and U.S. market data.",
        "tags": ["{a}", "{b}", "ETF comparison", "dividend ETF"],
    },
    "ja": {
        "title": "{a} vs {b} — ETF 比較",
        "desc": "{a}と{b}の並列比較：配当利回り・経費率・1年・5年リターン・リスクメモ。任意の投資額から年間インカムを試算できます。",
        "h_compare": "{a} vs {b}: 主な違い",
        "h_income": "インカムを試算する",
        "p_income": "上の投資額を入力して、{a}と{b}の年間・月間インカム推計を並べて比較してください。",
        "h_related": "関連ツール",
        "cta": "毎週金曜、配当ETFと米国市場のデータをまとめたニュースレターをお届けします。",
        "tags": ["{a}", "{b}", "ETF比較", "配当ETF"],
    },
    "ko": {
        "title": "{a} vs {b} — ETF 비교",
        "desc": "{a}과 {b}의 나란히 비교: 배당수익률·운용보수·1년·5년 수익률·리스크 메모. 투자 금액으로 연간 배당 수입을 추정해보세요.",
        "h_compare": "{a} vs {b}: 주요 차이점",
        "h_income": "배당 수입 추정하기",
        "p_income": "위 투자 금액을 입력해 {a}과 {b}의 연간·월간 배당 추정값을 나란히 비교하세요.",
        "h_related": "관련 도구",
        "cta": "매주 금요일, 배당 ETF와 미국 시장 데이터를 정리한 뉴스레터를 보내드립니다.",
        "tags": ["{a}", "{b}", "ETF 비교", "배당 ETF"],
    },
    "vi": {
        "title": "{a} vs {b} — So sánh ETF",
        "desc": "So sánh {a} và {b}: tỷ suất cổ tức, tỷ lệ chi phí, lợi nhuận 1 năm và 5 năm, ghi chú rủi ro. Ước tính thu nhập hàng năm từ bất kỳ số tiền đầu tư nào.",
        "h_compare": "{a} vs {b}: Điểm khác biệt chính",
        "h_income": "Ước tính thu nhập của bạn",
        "p_income": "Nhập số tiền đầu tư ở trên để so sánh thu nhập hàng năm và hàng tháng ước tính từ {a} và {b} song song.",
        "h_related": "Công cụ liên quan",
        "cta": "Mỗi thứ Sáu, chúng tôi gửi bản tin tổng hợp dữ liệu quỹ ETF cổ tức và thị trường Mỹ.",
        "tags": ["{a}", "{b}", "so sánh ETF", "ETF cổ tức"],
    },
    "id": {
        "title": "{a} vs {b} — Perbandingan ETF",
        "desc": "Perbandingan {a} dan {b} secara berdampingan: imbal hasil dividen, rasio biaya, return 1 tahun dan 5 tahun, catatan risiko. Perkirakan pendapatan tahunan dari jumlah investasi berapa pun.",
        "h_compare": "{a} vs {b}: Perbedaan Utama",
        "h_income": "Perkirakan Pendapatan Anda",
        "p_income": "Masukkan jumlah investasi di atas untuk membandingkan perkiraan pendapatan tahunan dan bulanan dari {a} dan {b} secara berdampingan.",
        "h_related": "Alat terkait",
        "cta": "Setiap Jumat kami mengirim buletin yang merangkum data ETF dividen dan pasar AS.",
        "tags": ["{a}", "{b}", "perbandingan ETF", "ETF dividen"],
    },
}


def _compare_related_links(lang, a, b, tpl):
    """Internal links: each ticker's dividend calculator + tools index."""
    a_lower = a.lower()
    b_lower = b.lower()
    lines = [
        f"- [{a} dividend calculator](/{lang}/tools/dividend-calculator/{a_lower}/)",
        f"- [{b} dividend calculator](/{lang}/tools/dividend-calculator/{b_lower}/)",
        f"- [{tpl['h_related']}](/{lang}/tools/)",
    ]
    return "\n".join(lines)


def generate_compare():
    data = _load_tickers()
    as_of = data.get("data_as_of", COMPARE_DATE)
    count = 0
    for lang in LANGS:
        tpl = COMPARE_TPL[lang]
        for (a, b) in COMPARE_PAIRS:
            intro, outro = COMPARE_ANGLES[lang][(a, b)]
            slug = f"{a.lower()}-vs-{b.lower()}"
            title = tpl["title"].format(a=a, b=b)
            desc = tpl["desc"].format(a=a, b=b)
            tags = ", ".join(f'"{t.format(a=a, b=b)}"' for t in tpl["tags"])
            related = _compare_related_links(lang, a, b, tpl)
            body = f"""---
title: "{title}"
description: "{desc}"
date: {as_of}T00:00:00+09:00
lastmod: {as_of}T00:00:00+09:00
draft: false
type: "tools"
tool: "compare"
ticker_a: "{a}"
ticker_b: "{b}"
schema: "Article"
author: "InvestIQs Editorial"
tags: [{tags}]
data_as_of: "{as_of}"
disclaimer: true
---

## {tpl['h_compare'].format(a=a, b=b)}

{intro}

{outro}

## {tpl['h_income'].format(a=a, b=b)}

{tpl['p_income'].format(a=a, b=b)}

## {tpl['h_related']}

{related}

{tpl['cta']}
"""
            out = CONTENT / lang / "tools" / "compare" / slug / "index.md"
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text(body, encoding="utf-8")
            count += 1
    print(f"generated {count} compare pages ({len(LANGS)} langs x {len(COMPARE_PAIRS)} pairs)")


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "generate"
    if cmd == "refresh":
        refresh()
    elif cmd == "generate":
        generate()
    elif cmd == "generate-compare":
        generate_compare()
    elif cmd == "all":
        refresh()
        generate()
    else:
        print(__doc__)
        sys.exit(1)
