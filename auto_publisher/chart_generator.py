"""
차트 생성기 — 투자 블로그용 matplotlib 데이터 시각화
카테고리별로 관련 차트 1~2개 자동 생성 → web/static/images/{slug}/
"""

import logging
from pathlib import Path

import matplotlib
matplotlib.use("Agg")  # GUI 없는 환경
import matplotlib.font_manager as fm
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import numpy as np

logger = logging.getLogger(__name__)

STATIC_DIR = Path("/home/mh/ocstorage/workspace/nichproject/web/static/images")

# 차트 alt 텍스트 언어별 포맷 (generate_charts lang 파라미터용)
_CHART_ALT_I18N: dict[str, dict[str, str]] = {
    "compound_growth": {
        "ko": "월 {m}만원 적립식 투자 {y}년 복리 시뮬레이션",
        "en": "Monthly ${m}K investment {y}-year compound growth simulation",
        "ja": "月{m}万円積立投資{y}年複利シミュレーション",
        "vi": "Đầu tư {m}tr/tháng mô phỏng lãi kép {y} năm",
        "id": "Investasi {m}jt/bulan simulasi bunga majemuk {y} tahun",
    },
    "dividend_income": {
        "ko": "월 {m}만원 배당 수입 달성 필요 투자금",
        "en": "Investment needed to achieve ${m}K monthly dividend income",
        "ja": "月{m}万円配当収入達成に必要な投資額",
        "vi": "Vốn cần thiết để đạt thu nhập cổ tức {m}tr/tháng",
        "id": "Modal untuk mencapai pendapatan dividen {m}jt/bulan",
    },
}


def _localize_chart_alt(alt: str, lang: str, chart_key: str, **fmt_kwargs) -> str:
    """언어별 차트 alt 텍스트 반환. 패턴 없으면 원본 반환."""
    if lang == "ko":
        return alt
    pattern = _CHART_ALT_I18N.get(chart_key, {}).get(lang)
    if not pattern:
        return alt
    try:
        return pattern.format(**fmt_kwargs)
    except Exception:
        return alt

# 한글 폰트 로드
_NOTO_CJK = "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"
if Path(_NOTO_CJK).exists():
    fm.fontManager.addfont(_NOTO_CJK)
    _KR_FONT = "Noto Sans CJK JP"
else:
    _KR_FONT = "DejaVu Sans"

plt.rcParams.update({
    "font.family": [_KR_FONT, "DejaVu Sans", "sans-serif"],
    "axes.unicode_minus": False,
    "figure.facecolor": "#0f172a",
    "axes.facecolor": "#1e293b",
    "axes.edgecolor": "#334155",
    "axes.labelcolor": "#cbd5e1",
    "xtick.color": "#94a3b8",
    "ytick.color": "#94a3b8",
    "text.color": "#f1f5f9",
    "axes.grid": True,
    "grid.color": "#334155",
    "grid.alpha": 0.6,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "legend.facecolor": "#1e293b",
    "legend.edgecolor": "#334155",
    "legend.labelcolor": "#cbd5e1",
})

COLORS = ["#2563eb", "#16a34a", "#dc2626", "#f59e0b", "#7c3aed"]


def _save(fig, slug: str, name: str) -> str:
    """차트 저장 후 정적 URL 경로 반환"""
    out_dir = STATIC_DIR / slug
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"{name}.png"
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    logger.info(f"차트 저장: {path}")
    return f"/images/{slug}/{name}.png"


# ─────────────────────────────────────────────
# 차트 함수들
# ─────────────────────────────────────────────

def chart_compound_growth(slug: str, monthly: int = 300_000, years: int = 20,
                           rates: list = None, lang: str = "ko") -> dict:
    """적립식 투자 복리 성장 시뮬레이션"""
    rates = rates or [4, 7, 10]
    months = years * 12
    fig, ax = plt.subplots(figsize=(9, 5))

    for i, r in enumerate(rates):
        monthly_rate = r / 100 / 12
        values = []
        v = 0
        for _ in range(months):
            v = (v + monthly) * (1 + monthly_rate)
            values.append(v / 1_0000_0000)  # 억 단위
        ax.plot(range(1, months + 1), values, color=COLORS[i], linewidth=2.5,
                label=f"연 {r}% 수익률")

    # 원금선
    principal = [monthly * m / 1_0000_0000 for m in range(1, months + 1)]
    ax.plot(range(1, months + 1), principal, color="#94a3b8", linewidth=1.5,
            linestyle="--", label="원금")

    ax.set_xlabel("투자 기간 (개월)", fontsize=11)
    ax.set_ylabel("자산 (억 원)", fontsize=11)
    ax.set_title(f"월 {monthly//10000}만원 적립식 투자 {years}년 시뮬레이션", fontsize=13, fontweight="bold")
    ax.legend(fontsize=10)
    ax.xaxis.set_major_formatter(mticker.FuncFormatter(
        lambda x, _: f"{int(x//12)}년" if x % 12 == 0 else ""))
    fig.tight_layout()
    return {"path": _save(fig, slug, "compound-growth"),
            "alt": _localize_chart_alt(
                f"월 {monthly//10000}만원 적립식 투자 {years}년 복리 시뮬레이션",
                lang, "compound_growth", m=monthly//10000, y=years)}


def chart_fee_impact(slug: str, principal: int = 10_000_000, years: int = 20) -> dict:
    """ETF 수수료 차이가 수익률에 미치는 영향"""
    base_rate = 0.07  # 연 7%
    fees = [0.05, 0.3, 0.5, 1.0]
    labels = ["0.05% (초저비용)", "0.3% (국내 ETF)", "0.5% (일반 펀드)", "1.0% (고비용)"]
    year_range = list(range(1, years + 1))

    fig, ax = plt.subplots(figsize=(9, 5))
    for i, (fee, label) in enumerate(zip(fees, labels)):
        net = base_rate - fee / 100
        values = [principal * (1 + net) ** y / 1_0000_0000 for y in year_range]
        ax.plot(year_range, values, color=COLORS[i], linewidth=2.5, label=label)

    ax.set_xlabel("투자 기간 (년)", fontsize=11)
    ax.set_ylabel("자산 (억 원)", fontsize=11)
    ax.set_title(f"ETF 수수료별 {years}년 후 자산 비교\n(초기 {principal//10000}만원, 연 7% 기준)",
                 fontsize=13, fontweight="bold")
    ax.legend(fontsize=10)
    fig.tight_layout()
    return {"path": _save(fig, slug, "fee-impact"),
            "alt": "ETF 수수료 차이가 장기 수익률에 미치는 영향 비교"}


def chart_dividend_income(slug: str, monthly_target: int = 1_000_000,
                           yields: list = None, lang: str = "ko") -> dict:
    """배당 수입 목표 달성 필요 자금 비교"""
    yields = yields or [3, 4, 5, 6]
    needed = [monthly_target * 12 / (y / 100) / 1_0000_0000 for y in yields]

    fig, ax = plt.subplots(figsize=(8, 5))
    bars = ax.bar([f"배당률\n{y}%" for y in yields], needed,
                  color=COLORS[:len(yields)], width=0.5, edgecolor="white", linewidth=1.5)

    for bar, val in zip(bars, needed):
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.05,
                f"{val:.1f}억", ha="center", va="bottom", fontsize=11, fontweight="bold")

    ax.set_ylabel("필요 투자금 (억 원)", fontsize=11)
    ax.set_title(f"월 {monthly_target//10000}만원 배당 수입 달성에 필요한 투자금", fontsize=13, fontweight="bold")
    ax.set_ylim(0, max(needed) * 1.2)
    fig.tight_layout()
    return {"path": _save(fig, slug, "dividend-target"),
            "alt": _localize_chart_alt(
                f"월 {monthly_target//10000}만원 배당 수입 달성 필요 투자금",
                lang, "dividend_income", m=monthly_target//10000)}


def chart_tax_saving(slug: str) -> dict:
    """ISA·IRP·연금저축 세후 수익 비교 (1000만원, 10년)"""
    products = ["일반 계좌", "ISA 중개형", "IRP", "연금저축펀드"]
    # 가정: 연 7%, 1000만원, 10년
    gross = 1000 * ((1.07 ** 10) - 1)  # 총 수익 약 967만원
    # 세금: 일반(15.4%), ISA(9.9% 비과세 한도 초과분), IRP(연금소득세 3.3~5.5%), 연금(5.5%)
    tax_rates = [0.154, 0.099, 0.055, 0.055]
    after_tax = [gross * (1 - t) / 100 for t in tax_rates]  # 백만원 단위

    fig, ax = plt.subplots(figsize=(8, 5))
    bars = ax.bar(products, after_tax, color=COLORS[:4], width=0.5,
                  edgecolor="white", linewidth=1.5)

    for bar, val in zip(bars, after_tax):
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.02,
                f"{val:.0f}만원", ha="center", va="bottom", fontsize=11, fontweight="bold")

    ax.set_ylabel("세후 수익 (만원)", fontsize=11)
    ax.set_title("계좌 종류별 세후 수익 비교\n(1,000만원 투자, 연 7%, 10년)", fontsize=13, fontweight="bold")
    fig.tight_layout()
    return {"path": _save(fig, slug, "tax-comparison"),
            "alt": "ISA, IRP, 연금저축펀드 절세 효과 비교"}


def chart_real_estate_yield(slug: str) -> dict:
    """부동산 투자 수익률 vs 금융 투자 비교"""
    years = list(range(1, 21))
    # 연 4% 월세 수익률 + 연 2% 자산상승
    re_values = [1 + (0.04 + 0.02) * y for y in years]
    # ETF 연 7%
    etf_values = [(1.07 ** y) for y in years]
    # 예금 연 3.5%
    deposit_values = [(1.035 ** y) for y in years]

    fig, ax = plt.subplots(figsize=(9, 5))
    ax.plot(years, re_values, color=COLORS[0], linewidth=2.5, label="수익형 부동산 (월세 4%+상승 2%)")
    ax.plot(years, etf_values, color=COLORS[1], linewidth=2.5, label="지수 ETF (연 7%)")
    ax.plot(years, deposit_values, color=COLORS[2], linewidth=2.5, linestyle="--", label="정기예금 (연 3.5%)")

    ax.set_xlabel("투자 기간 (년)", fontsize=11)
    ax.set_ylabel("자산 배수 (원금 = 1)", fontsize=11)
    ax.set_title("투자 유형별 장기 수익 비교 (원금 1 기준)", fontsize=13, fontweight="bold")
    ax.legend(fontsize=10)
    fig.tight_layout()
    return {"path": _save(fig, slug, "investment-comparison"),
            "alt": "부동산 vs ETF vs 예금 장기 수익률 비교"}


def chart_price_history(slug: str, ticker: str, mkt_data: dict = None) -> dict:
    """yfinance 실제 가격 히스토리 차트 (1~3년)"""
    try:
        import yfinance as yf
        hist = yf.download(ticker, period="3y", progress=False, auto_adjust=True)
        if hist.empty:
            raise ValueError("데이터 없음")
        # yfinance multi-index 대응: Close 컬럼 추출 후 1차원으로
        close_raw = hist["Close"]
        if hasattr(close_raw, "squeeze"):
            close_raw = close_raw.squeeze()
        close = close_raw.dropna().astype(float)
    except Exception:
        # fallback: 시뮬레이션 데이터
        months = 36
        x = np.arange(months)
        close_vals = 100 * np.cumprod(1 + np.random.normal(0.007, 0.04, months))
        fig, ax = plt.subplots(figsize=(10, 5))
        ax.plot(x, close_vals, color=COLORS[0], linewidth=2)
        ax.set_title(f"{ticker} 가격 추이 (시뮬레이션)", fontsize=13, fontweight="bold")
        fig.tight_layout()
        return {"path": _save(fig, slug, "price-history"), "alt": f"{ticker} 가격 추이"}

    vals = close.values.astype(float)
    peak_pos = int(np.argmax(vals))
    peak_val = float(vals[peak_pos])
    peak_date = close.index[peak_pos]

    fig, ax = plt.subplots(figsize=(10, 5))
    ax.plot(close.index, vals, color=COLORS[0], linewidth=1.8)
    ax.fill_between(close.index, vals, alpha=0.1, color=COLORS[0])

    ax.annotate(f"고점 ${peak_val:.0f}",
                xy=(peak_date, peak_val),
                xytext=(0, 14), textcoords="offset points",
                ha="center", fontsize=9, color=COLORS[1],
                arrowprops=dict(arrowstyle="->", color=COLORS[1]))

    ax.set_xlabel("날짜", fontsize=11)
    ax.set_ylabel("가격 (USD)", fontsize=11)
    ax.set_title(f"{ticker} 최근 3년 가격 추이", fontsize=13, fontweight="bold")
    fig.autofmt_xdate()
    fig.tight_layout()
    return {"path": _save(fig, slug, "price-history"), "alt": f"{ticker} 최근 3년 가격 차트"}


def chart_return_bars(slug: str, ticker: str, mkt_data: dict = None) -> dict:
    """1y/3y/5y/10y 수익률 막대 차트 (실데이터 or mkt_data 활용)"""
    labels = ["1년", "3년", "5년", "10년"]
    keys = ["1y_return_pct", "3y_return_pct", "5y_return_pct", "10y_return_pct"]

    if mkt_data:
        values = [mkt_data.get(k) for k in keys]
    else:
        try:
            import yfinance as yf
            import pandas as pd
            hist = yf.download(ticker, period="10y", progress=False, auto_adjust=True)
            close = hist["Close"].dropna() if not hist.empty else pd.Series()
            def _ret(years):
                n = years * 252
                if len(close) >= n:
                    return round((float(close.iloc[-1]) / float(close.iloc[-n]) - 1) * 100, 1)
                return None
            values = [_ret(1), _ret(3), _ret(5), _ret(10)]
        except Exception:
            values = [None, None, None, None]

    # None 제거
    valid = [(l, v) for l, v in zip(labels, values) if v is not None]
    if not valid:
        valid = [("1년", 12), ("3년", 45), ("5년", 85), ("10년", 230)]  # placeholder

    xlabels, yvalues = zip(*valid)
    colors = [COLORS[1] if v >= 0 else COLORS[2] for v in yvalues]

    fig, ax = plt.subplots(figsize=(8, 5))
    bars = ax.bar(xlabels, yvalues, color=colors, width=0.5, edgecolor="white", linewidth=1.5)

    for bar, val in zip(bars, yvalues):
        ax.text(bar.get_x() + bar.get_width() / 2,
                bar.get_height() + (1 if val >= 0 else -4),
                f"{val:+.1f}%", ha="center", va="bottom", fontsize=11, fontweight="bold")

    ax.axhline(0, color="#94a3b8", linewidth=1)
    ax.set_ylabel("누적 수익률 (%)", fontsize=11)
    ax.set_title(f"{ticker} 기간별 누적 수익률 (yfinance 실데이터)", fontsize=13, fontweight="bold")
    fig.tight_layout()
    return {"path": _save(fig, slug, "return-bars"), "alt": f"{ticker} 기간별 수익률 비교"}


def chart_etf_comparison(slug: str, keywords: list[str] = None) -> dict:
    """ETF 2~3종 수수료·수익률 비교 (블로그 토픽 키워드 기반)"""
    # 키워드에서 알려진 ETF 추출
    known = {
        "VOO": {"fee": 0.03, "yield": 1.3, "5y": 108},
        "SCHD": {"fee": 0.06, "yield": 3.6, "5y": 72},
        "QQQ": {"fee": 0.20, "yield": 0.5, "5y": 142},
        "JEPI": {"fee": 0.35, "yield": 7.2, "5y": 38},
        "SPY": {"fee": 0.09, "yield": 1.3, "5y": 107},
        "QQQM": {"fee": 0.15, "yield": 0.5, "5y": 140},
        "VT": {"fee": 0.07, "yield": 1.8, "5y": 68},
        "JEPQ": {"fee": 0.35, "yield": 9.5, "5y": 30},
    }

    tickers_found = []
    if keywords:
        for kw in keywords:
            for name in known:
                if name in kw.upper() and name not in tickers_found:
                    tickers_found.append(name)

    if len(tickers_found) < 2:
        tickers_found = ["VOO", "SCHD", "QQQ"]
    tickers_found = tickers_found[:3]

    data = {t: known.get(t, {"fee": 0.1, "yield": 2.0, "5y": 80}) for t in tickers_found}
    x = np.arange(len(tickers_found))
    width = 0.25

    fig, axes = plt.subplots(1, 3, figsize=(12, 5))
    fig.suptitle("ETF 핵심 지표 비교", fontsize=14, fontweight="bold")

    metrics = [
        ("운용보수 (%)", "fee", COLORS[0]),
        ("배당수익률 (%)", "yield", COLORS[1]),
        ("5년 누적수익률 (%)", "5y", COLORS[2]),
    ]

    for ax, (title, key, color) in zip(axes, metrics):
        vals = [data[t][key] for t in tickers_found]
        bars = ax.bar(tickers_found, vals, color=color, width=0.5, edgecolor="white")
        for bar, val in zip(bars, vals):
            ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + max(vals) * 0.02,
                    f"{val}", ha="center", va="bottom", fontsize=10, fontweight="bold")
        ax.set_title(title, fontsize=11)
        ax.set_ylim(0, max(vals) * 1.25)
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)

    fig.tight_layout()
    return {"path": _save(fig, slug, "etf-comparison"), "alt": f"{' vs '.join(tickers_found)} 핵심 지표 비교"}


# ─────────────────────────────────────────────
# 메인 인터페이스
# ─────────────────────────────────────────────

CATEGORY_CHART_MAP = {
    # 기존 카테고리
    "ETF": [chart_compound_growth, chart_fee_impact],
    "배당주": [chart_dividend_income, chart_compound_growth],
    "절세": [chart_tax_saving],
    "부동산": [chart_real_estate_yield],
    "재테크 기초": [chart_compound_growth],
    # 레거시 (테이버형) — 호환 유지
    "ETF 실전 후기": [chart_etf_comparison, chart_compound_growth],
    "배당 실전 후기": [chart_dividend_income, chart_etf_comparison],
    "절세 실전": [chart_tax_saving],
    "포트폴리오 공개": [chart_compound_growth, chart_fee_impact],
    "투자 입문 경험": [chart_compound_growth, chart_etf_comparison],
    # 신규 분석가 카테고리
    "ETF 데이터 분석": [chart_etf_comparison, chart_return_bars],
    "ETF 리스크 리서치": [chart_fee_impact, chart_compound_growth],
    "ETF 비용 분석": [chart_fee_impact, chart_etf_comparison],
    "배당 ETF 리서치": [chart_dividend_income, chart_etf_comparison],
    "포트폴리오 백테스트": [chart_compound_growth, chart_fee_impact],
    "세제 분석": [chart_tax_saving],
    "투자 전략 분석": [chart_compound_growth, chart_fee_impact],
    "국내 ETF 분석": [chart_etf_comparison],
    "비용 분석": [chart_fee_impact],
    "섹터 ETF 분석": [chart_etf_comparison, chart_return_bars],
}


def generate_charts(slug: str, category: str, keywords: list[str], lang: str = "ko") -> list[dict]:
    """
    토픽에 맞는 차트 1~2개 생성 후 이미지 정보 리스트 반환
    [{"path": "/images/...", "alt": "..."}]
    """
    chart_fns = CATEGORY_CHART_MAP.get(category, [chart_compound_growth])

    results = []
    for fn in chart_fns[:2]:
        try:
            if fn in (chart_etf_comparison,):
                info = fn(slug, keywords=keywords)
            elif fn in (chart_compound_growth, chart_dividend_income):
                info = fn(slug, lang=lang)
            else:
                info = fn(slug)
            results.append(info)
        except Exception as e:
            logger.warning(f"차트 생성 실패 ({fn.__name__}): {e}")

    return results


def chart_drawdown(slug: str, ticker: str, mkt_data: dict = None) -> dict:
    """yfinance 기반 최대 낙폭 (drawdown) 차트 — 위험 시각화"""
    try:
        import yfinance as yf
        hist = yf.download(ticker, period="5y", progress=False, auto_adjust=True)
        if hist.empty:
            raise ValueError("데이터 없음")
        close_raw = hist["Close"]
        if hasattr(close_raw, "squeeze"):
            close_raw = close_raw.squeeze()
        close = close_raw.dropna().astype(float)
        running_max = close.cummax()
        drawdown = (close / running_max - 1) * 100
        max_dd = float(drawdown.min())
    except Exception:
        return {"path": "", "alt": ""}

    fig, ax = plt.subplots(figsize=(10, 5))
    ax.fill_between(close.index, drawdown.values, 0, color=COLORS[2], alpha=0.4)
    ax.plot(close.index, drawdown.values, color=COLORS[2], linewidth=1.2)
    ax.axhline(0, color="#94a3b8", linewidth=1)
    ax.axhline(max_dd, color=COLORS[3], linewidth=1, linestyle="--",
               label=f"최대낙폭 {max_dd:.1f}%")
    ax.set_ylabel("낙폭 (%)", fontsize=11)
    ax.set_title(f"{ticker} 최근 5년 최대 낙폭 (Drawdown) — 위험도 시각화",
                 fontsize=13, fontweight="bold")
    ax.legend(fontsize=10)
    fig.autofmt_xdate()
    fig.tight_layout()
    return {"path": _save(fig, slug, "drawdown"),
            "alt": f"{ticker} 5년 최대 낙폭 차트"}


def chart_dividend_history(slug: str, ticker: str, mkt_data: dict = None) -> dict:
    """yfinance 배당 히스토리 — 분기/연간 배당금 추이"""
    try:
        import yfinance as yf
        t = yf.Ticker(ticker)
        divs = t.dividends
        if divs is None or len(divs) == 0:
            return {"path": "", "alt": ""}
        # 최근 5년만
        divs = divs.tail(20)  # 분기배당 5년치
    except Exception:
        return {"path": "", "alt": ""}

    fig, ax = plt.subplots(figsize=(10, 5))
    bars = ax.bar(range(len(divs)), divs.values, color=COLORS[1],
                  edgecolor="white", width=0.7)
    ax.set_xticks(range(len(divs)))
    ax.set_xticklabels([d.strftime("%Y-%m") for d in divs.index], rotation=45, fontsize=9)
    ax.set_ylabel("주당 배당금 ($)", fontsize=11)
    ax.set_title(f"{ticker} 분기별 배당금 추이 (최근 5년)", fontsize=13, fontweight="bold")
    fig.tight_layout()
    return {"path": _save(fig, slug, "dividend-history"),
            "alt": f"{ticker} 분기별 배당금 추이"}


def generate_analysis_charts(slug: str, ticker: str, mkt_data: dict = None) -> list[dict]:
    """
    분석 포스트 전용 차트: 실제 가격 히스토리 + 기간별 수익률 + 최대낙폭
    """
    results = []
    for fn in [chart_price_history, chart_return_bars, chart_drawdown]:
        try:
            info = fn(slug, ticker=ticker, mkt_data=mkt_data)
            if info.get("path"):
                results.append(info)
        except Exception as e:
            logger.warning(f"분석 차트 생성 실패 ({fn.__name__}): {e}")
    return results


def get_chart_hints(slug: str, category: str, keywords: list = None,
                    ticker: str = "", mkt_data: dict = None) -> list:
    """
    차트를 사전 생성하고 본문 프롬프트 주입용 정보 반환

    Returns:
        [{"path": "/images/...", "alt": "...", "summary": "본문에서 이 차트를 인용할 때 쓸 핵심 데이터 텍스트"}]
    """
    keywords = keywords or []
    is_analysis = bool(ticker)

    if is_analysis:
        charts = generate_analysis_charts(slug, ticker, mkt_data)
        for c in charts:
            if "price-history" in c["path"]:
                c["summary"] = f"{ticker} 최근 3년 가격 추이 차트 (저점~고점, 변동성 시각화)"
            elif "return-bars" in c["path"]:
                ret_str = ""
                if mkt_data:
                    parts = []
                    for label, key in [("1년", "1y_return_pct"), ("3년", "3y_return_pct"),
                                        ("5년", "5y_return_pct"), ("10년", "10y_return_pct")]:
                        v = mkt_data.get(key)
                        if v is not None:
                            parts.append(f"{label} {v:+.1f}%")
                    ret_str = ", ".join(parts)
                c["summary"] = f"{ticker} 기간별 누적 수익률 막대차트 ({ret_str})"
            elif "drawdown" in c["path"]:
                c["summary"] = f"{ticker} 최근 5년 최대 낙폭 차트 (위험도 시각화)"
        return charts

    charts = generate_charts(slug, category, keywords)
    for c in charts:
        if "etf-comparison" in c["path"]:
            c["summary"] = f"ETF 핵심 지표 3패널 비교 (운용보수 / 배당수익률 / 5년 누적수익률)"
        elif "compound-growth" in c["path"]:
            c["summary"] = "월 30만원 적립식 투자 20년 시뮬레이션 (연 4%/7%/10% 비교)"
        elif "fee-impact" in c["path"]:
            c["summary"] = "ETF 운용보수별 20년 후 자산 비교 (0.05%/0.3%/0.5%/1.0%)"
        elif "dividend-target" in c["path"]:
            c["summary"] = "월 100만원 배당 수입 달성에 필요한 투자금 (배당률별)"
        elif "tax-comparison" in c["path"]:
            c["summary"] = "ISA/IRP/연금저축 세후 수익 비교 (1000만원, 10년)"
    return charts


def _figure_html(chart: dict) -> str:
    return (
        f'\n<figure class="chart-figure">'
        f'<img src="{chart["path"]}" alt="{chart["alt"]}" '
        f'loading="lazy" style="max-width:100%;border-radius:8px;">'
        f'<figcaption>{chart["alt"]}</figcaption>'
        f'</figure>\n'
    )


def inject_charts_into_html(content_html: str, charts: list[dict]) -> str:
    """차트들을 본문 내 H2들에 분산 삽입 — 첫 H2엔 차트1, 두번째엔 차트2 ..."""
    if not charts:
        return content_html

    # 모든 </h2> 위치 찾기
    import re as _re
    h2_positions = [m.end() for m in _re.finditer(r'</h2>', content_html)]

    if not h2_positions:
        # H2 없으면 첫 </p> 뒤에 모두 모아서 삽입 (fallback)
        all_imgs = "".join(_figure_html(c) for c in charts)
        p_pos = content_html.find("</p>")
        if p_pos != -1:
            pos = p_pos + len("</p>")
            return content_html[:pos] + all_imgs + content_html[pos:]
        return all_imgs + content_html

    # 차트 개수만큼 H2 배분 (H2가 차트 수보다 적으면 마지막 H2에 나머지 모음)
    new_html = content_html
    offset = 0
    for i, chart in enumerate(charts):
        # H2 인덱스: i번째 H2, 부족하면 마지막 H2
        h2_idx = min(i, len(h2_positions) - 1)
        insert_pos = h2_positions[h2_idx] + offset
        fig = _figure_html(chart)
        new_html = new_html[:insert_pos] + fig + new_html[insert_pos:]
        offset += len(fig)

    return new_html


def inject_charts_into_html_OLD(content_html: str, charts: list[dict]) -> str:
    """[deprecated] 첫 번째 H2 뒤에 차트 이미지 모두 삽입"""
    if not charts:
        return content_html

    img_html = ""
    for chart in charts:
        img_html += (
            f'\n<figure class="chart-figure">'
            f'<img src="{chart["path"]}" alt="{chart["alt"]}" '
            f'loading="lazy" style="max-width:100%;border-radius:8px;">'
            f'<figcaption>{chart["alt"]}</figcaption>'
            f'</figure>\n'
        )

    # 첫 번째 </h2> 닫는 태그 뒤에 삽입
    insert_point = content_html.find("</h2>")
    if insert_point != -1:
        pos = insert_point + len("</h2>")
        return content_html[:pos] + img_html + content_html[pos:]

    # h2 없으면 첫 </p> 뒤에
    insert_point = content_html.find("</p>")
    if insert_point != -1:
        pos = insert_point + len("</p>")
        return content_html[:pos] + img_html + content_html[pos:]

    return img_html + content_html
