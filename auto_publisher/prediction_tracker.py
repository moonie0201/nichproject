"""예측 추적 시스템 — 발행된 분석 신호의 60일 후 실적 검증."""
import json
import math
import sqlite3
from datetime import date, timedelta
from pathlib import Path

STATIC_JSON = Path(__file__).parent.parent / "web" / "static" / "data" / "prediction-accuracy.json"


_CREATE_SQL = """
CREATE TABLE IF NOT EXISTS predictions (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    slug        TEXT NOT NULL,
    ticker      TEXT NOT NULL,
    signal      TEXT NOT NULL,
    price_at_publish REAL NOT NULL,
    published_at TEXT NOT NULL,
    verified_at  TEXT,
    price_at_verify REAL,
    return_pct   REAL,
    direction_correct INTEGER,
    alpha_vs_spy REAL
)
"""


def _wilson_ci(correct: int, total: int, z: float = 1.96) -> tuple[float, float]:
    p = correct / total
    denom = 1 + z**2 / total
    center = (p + z**2 / (2 * total)) / denom
    margin = (z * math.sqrt(p * (1 - p) / total + z**2 / (4 * total**2))) / denom
    return round(max(0, center - margin), 3), round(min(1, center + margin), 3)


class PredictionTracker:
    def __init__(self, db_path: str = "auto_publisher/data/predictions.db"):
        self._db = db_path
        self._shared = None
        if db_path == ":memory:":
            self._shared = sqlite3.connect(":memory:", check_same_thread=False)
            self._shared.row_factory = sqlite3.Row
        conn = self._conn()
        conn.execute(_CREATE_SQL)
        conn.commit()
        # migrate: add alpha_vs_spy if table existed before this column
        try:
            conn.execute("ALTER TABLE predictions ADD COLUMN alpha_vs_spy REAL")
            conn.commit()
        except Exception:
            pass  # already exists
        if not self._shared:
            conn.close()

    def _conn(self) -> sqlite3.Connection:
        if self._shared is not None:
            return self._shared
        conn = sqlite3.connect(self._db)
        conn.row_factory = sqlite3.Row
        return conn

    def record(
        self,
        slug: str,
        ticker: str,
        signal: str,
        price_at_publish: float,
        published_at: str,
    ) -> None:
        conn = self._conn()
        conn.execute(
            "INSERT INTO predictions (slug, ticker, signal, price_at_publish, published_at) "
            "VALUES (?, ?, ?, ?, ?)",
            (slug, ticker, signal, price_at_publish, published_at),
        )
        conn.commit()
        if not self._shared:
            conn.close()

    def pending_verification(self) -> list[dict]:
        """미검증 레코드 전체 반환 (날짜 무관)."""
        conn = self._conn()
        rows = conn.execute(
            "SELECT * FROM predictions WHERE verified_at IS NULL",
        ).fetchall()
        if not self._shared:
            conn.close()
        return [dict(r) for r in rows]

    def run_verification(self, current_prices: dict[str, float]) -> list[dict]:
        """60일 경과된 pending 레코드를 current_prices로 검증 후 결과 반환."""
        cutoff = (date.today() - timedelta(days=60)).isoformat()
        pending = [r for r in self.pending_verification() if r["published_at"] <= cutoff]
        results = []
        conn = self._conn()
        today = date.today().isoformat()

        # SPY 동기간 수익률 (per-record, cached)
        spy_ret_cache: dict[str, float | None] = {}

        def _spy_ret_for(pub_date: str) -> float | None:
            if pub_date in spy_ret_cache:
                return spy_ret_cache[pub_date]
            try:
                import yfinance as yf
                sub = yf.Ticker("SPY").history(start=pub_date, end=today)
                if not sub.empty:
                    r = (float(sub["Close"].iloc[-1]) - float(sub["Close"].iloc[0])) / float(sub["Close"].iloc[0]) * 100
                    spy_ret_cache[pub_date] = round(r, 3)
                    return spy_ret_cache[pub_date]
            except Exception:
                pass
            spy_ret_cache[pub_date] = None
            return None

        for row in pending:
            ticker = row["ticker"]
            if ticker not in current_prices:
                continue
            price_now = current_prices[ticker]
            ret = (price_now - row["price_at_publish"]) / row["price_at_publish"] * 100
            signal = row["signal"].lower()
            if signal in ("bullish", "buy", "strong_buy"):
                correct = ret > 0
            elif signal in ("bearish", "sell", "strong_sell"):
                correct = ret < 0
            else:  # hold / neutral
                correct = True  # hold은 방향 무관 — 큰 손실이 없으면 OK

            spy_ret = _spy_ret_for(row["published_at"])
            alpha = round(ret - spy_ret, 3) if spy_ret is not None else None

            conn.execute(
                "UPDATE predictions SET verified_at=?, price_at_verify=?, "
                "return_pct=?, direction_correct=?, alpha_vs_spy=? WHERE id=?",
                (today, price_now, round(ret, 3), int(correct), alpha, row["id"]),
            )
            results.append({
                **row,
                "verified_at": today,
                "price_at_verify": price_now,
                "return_pct": round(ret, 3),
                "direction_correct": correct,
                "alpha_vs_spy": alpha,
            })
        conn.commit()
        if not self._shared:
            conn.close()
        return results

    def accuracy_summary(self) -> dict:
        """검증 완료된 레코드의 방향 정확도 및 KPI 요약."""
        conn = self._conn()
        rows = conn.execute(
            "SELECT direction_correct, return_pct, alpha_vs_spy "
            "FROM predictions WHERE verified_at IS NOT NULL"
        ).fetchall()
        if not self._shared:
            conn.close()
        total = len(rows)
        if total == 0:
            return {"total_verified": 0, "direction_accuracy": None}

        correct = sum(r["direction_correct"] for r in rows)
        result: dict = {
            "total_verified": total,
            "direction_accuracy": round(correct / total, 3),
        }
        if total < 30:
            result["insufficient_data"] = True
        else:
            lower, upper = _wilson_ci(correct, total)
            result["wilson_ci_lower"] = lower
            result["wilson_ci_upper"] = upper

        # additional KPIs (always computed when total > 0)
        correct_count = sum(r["direction_correct"] for r in rows)
        result["hit_rate"] = round(correct_count / total, 3)

        returns = [r["return_pct"] for r in rows if r["return_pct"] is not None]
        if returns:
            result["avg_return_pct"] = round(sum(returns) / len(returns), 3)
            pos_sum = sum(r for r in returns if r > 0)
            neg_sum = sum(abs(r) for r in returns if r < 0)
            result["profit_factor"] = round(pos_sum / neg_sum, 3) if neg_sum != 0 else None
        else:
            result["avg_return_pct"] = None
            result["profit_factor"] = None

        alphas = [r["alpha_vs_spy"] for r in rows if r["alpha_vs_spy"] is not None]
        result["alpha_vs_spy"] = round(sum(alphas) / len(alphas), 3) if alphas else None

        return result

    def export_json(self, path: str | Path = STATIC_JSON) -> None:
        """트랙레코드를 정적 JSON으로 내보내기 (Hugo 페이지용)."""
        conn = self._conn()
        records = [dict(r) for r in conn.execute(
            "SELECT slug, ticker, signal, price_at_publish, published_at, "
            "verified_at, price_at_verify, return_pct, direction_correct, alpha_vs_spy "
            "FROM predictions ORDER BY published_at DESC LIMIT 100"
        ).fetchall()]
        pending = [r for r in records if r["verified_at"] is None]
        if not self._shared:
            conn.close()
        summary = self.accuracy_summary()
        out = {
            **summary,
            "pending_count": len(pending),
            "records": records,
            "last_updated": date.today().isoformat(),
        }
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        Path(path).write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
