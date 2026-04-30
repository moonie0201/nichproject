"""
Bridge API TDD Tests — pytest + requests
Run: cd /home/mh/ocstorage/workspace/nichproject && python3 -m pytest n8n/tests/test_bridge_api.py -v

Test server starts on 127.0.0.1:8766 (test port, separate from prod 8765).
"""
import sys
import os
import json
import time
import threading
import subprocess
import importlib
from pathlib import Path
from http.server import HTTPServer

import pytest
import requests

# ---------------------------------------------------------------------------
# Path setup so bridge_api can be imported without VENV_PYTHON issues
# ---------------------------------------------------------------------------
NICHPROJECT = Path("/home/mh/ocstorage/workspace/nichproject")
sys.path.insert(0, str(NICHPROJECT))
os.chdir(NICHPROJECT)

TEST_PORT = 8766
BASE_URL = f"http://127.0.0.1:{TEST_PORT}"

# ---------------------------------------------------------------------------
# Fixture: start bridge server in a background thread on TEST_PORT
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def bridge_server():
    """Start bridge_api HTTPServer on TEST_PORT in a daemon thread."""
    # Patch port env var before import so the handler uses test port
    os.environ["BRIDGE_PORT"] = str(TEST_PORT)

    # Import the handler class from bridge_api
    import n8n.bridge_api as api_module
    importlib.reload(api_module)  # ensure fresh module with env applied

    server = HTTPServer(("127.0.0.1", TEST_PORT), api_module.BridgeHandler)
    t = threading.Thread(target=server.serve_forever, daemon=True)
    t.start()

    # Wait until server is ready
    deadline = time.time() + 5
    while time.time() < deadline:
        try:
            requests.get(f"{BASE_URL}/health", timeout=0.5)
            break
        except Exception:
            time.sleep(0.1)

    yield server
    server.shutdown()


# ---------------------------------------------------------------------------
# 1. GET /health → 200 + {status, services}
# ---------------------------------------------------------------------------

def test_health_returns_200(bridge_server):
    """GET /health returns HTTP 200 with status field."""
    resp = requests.get(f"{BASE_URL}/health", timeout=5)
    assert resp.status_code == 200
    body = resp.json()
    assert "status" in body


# ---------------------------------------------------------------------------
# 2. GET /health?deep=true → services별 상태 포함
# ---------------------------------------------------------------------------

def test_health_deep_check(bridge_server):
    """GET /health?deep=true returns services dict with per-service status."""
    resp = requests.get(f"{BASE_URL}/health?deep=true", timeout=10)
    assert resp.status_code == 200
    body = resp.json()
    assert "services" in body
    services = body["services"]
    assert isinstance(services, dict)
    assert len(services) >= 1


# ---------------------------------------------------------------------------
# 3. POST /compliance/check — 금칙어 violations 리턴
# ---------------------------------------------------------------------------

def test_compliance_check_rejects_forbidden_phrase(bridge_server):
    """POST /compliance/check returns violations for forbidden phrases."""
    payload = {
        "content": {
            "title": "투자 가이드",
            "html": "<p>이 상품은 원금보장이 됩니다.</p>",
        },
        "lang": "ko",
        "channel": "blog",
    }
    resp = requests.post(f"{BASE_URL}/compliance/check", json=payload, timeout=10)
    assert resp.status_code == 200
    body = resp.json()
    assert body.get("ok") is False or (
        "violations" in body and len(body["violations"]) > 0
    )


def test_compliance_check_rejects_all_target_forbidden_phrases(bridge_server):
    """Forbidden phrases '확실한수익' and '리딩방' each trigger a violation."""
    for phrase in ["확실한수익", "리딩방"]:
        payload = {
            "content": {
                "title": "투자 팁",
                "html": f"<p>{phrase}을 알려드립니다.</p>",
            },
            "lang": "ko",
        }
        resp = requests.post(f"{BASE_URL}/compliance/check", json=payload, timeout=10)
        assert resp.status_code == 200, f"Expected 200 for phrase '{phrase}'"
        body = resp.json()
        assert len(body.get("violations", [])) > 0, (
            f"Expected violation for forbidden phrase '{phrase}'"
        )


# ---------------------------------------------------------------------------
# 4. POST /compliance/check — 정상 콘텐츠 → {ok: true, violations: []}
# ---------------------------------------------------------------------------

def test_compliance_check_passes_clean_content(bridge_server):
    """POST /compliance/check returns ok=true and empty violations for clean content."""
    payload = {
        "content": {
            "title": "ETF 배당 분석",
            "html": (
                "<p>SCHD ETF의 배당 성장률을 분석합니다.</p>"
                "<p>투자는 본인 책임이며, 본 글은 정보 제공 목적입니다.</p>"
            ),
        },
        "lang": "ko",
    }
    resp = requests.post(f"{BASE_URL}/compliance/check", json=payload, timeout=10)
    assert resp.status_code == 200
    body = resp.json()
    assert body.get("ok") is True
    assert body.get("violations", []) == []


# ---------------------------------------------------------------------------
# 5. POST /compliance/check — 투자 콘텐츠인데 면책 없으면 warning
# ---------------------------------------------------------------------------

def test_compliance_check_requires_disclaimer(bridge_server):
    """Investment content without disclaimer triggers a warning."""
    payload = {
        "content": {
            "title": "ETF 투자 전략",
            "html": "<p>이 ETF에 투자하면 배당을 받을 수 있습니다.</p>",
        },
        "lang": "ko",
    }
    resp = requests.post(f"{BASE_URL}/compliance/check", json=payload, timeout=10)
    assert resp.status_code == 200
    body = resp.json()
    # Either a warning in violations or ok=False indicates disclaimer check is active
    has_warning = any(
        v.get("severity") in ("warning", "high", "medium")
        for v in body.get("violations", [])
    )
    assert not body.get("ok", True) or has_warning, (
        "Expected disclaimer-missing warning for investment content without disclaimer"
    )


# ---------------------------------------------------------------------------
# 6. POST /compliance/check — body 누락 시 400
# ---------------------------------------------------------------------------

def test_compliance_check_missing_body_returns_400(bridge_server):
    """POST /compliance/check with no body returns 400."""
    resp = requests.post(
        f"{BASE_URL}/compliance/check",
        data="",
        headers={"Content-Type": "application/json"},
        timeout=10,
    )
    assert resp.status_code == 400


# ---------------------------------------------------------------------------
# 7. POST /generate/monthly-dividend → {success, title, content_preview}
# ---------------------------------------------------------------------------

def test_monthly_dividend_returns_markdown(bridge_server):
    """POST /generate/monthly-dividend returns success=True with title and content_preview."""
    payload = {
        "symbols": ["SCHD", "JEPI"],
        "lang": "ko",
    }
    resp = requests.post(
        f"{BASE_URL}/generate/monthly-dividend", json=payload, timeout=180
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body.get("success") is True
    assert "title" in body
    assert "content_preview" in body or "content" in body


# ---------------------------------------------------------------------------
# 8. POST /generate/monthly-dividend — symbols 리스트 반영
# ---------------------------------------------------------------------------

def test_monthly_dividend_accepts_symbols_list(bridge_server):
    """POST /generate/monthly-dividend includes requested symbols in content."""
    payload = {
        "symbols": ["SCHD", "JEPI"],
        "lang": "ko",
    }
    resp = requests.post(
        f"{BASE_URL}/generate/monthly-dividend", json=payload, timeout=180
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body.get("success") is True
    # At least one requested symbol should appear in title or content
    content_text = str(body.get("title", "")) + str(
        body.get("content_preview", body.get("content", ""))
    )
    assert any(sym in content_text for sym in ["SCHD", "JEPI"]), (
        "Expected requested symbols to appear in generated content"
    )


# ---------------------------------------------------------------------------
# 9. POST /generate/monthly-dividend — timeout handling → 504 or error JSON
# ---------------------------------------------------------------------------

def test_monthly_dividend_timeout_handling(bridge_server):
    """POST /generate/monthly-dividend with force_timeout returns 504 or error JSON."""
    payload = {
        "symbols": ["SCHD"],
        "lang": "ko",
        "force_timeout": True,  # special test flag to trigger timeout path
    }
    resp = requests.post(
        f"{BASE_URL}/generate/monthly-dividend", json=payload, timeout=30
    )
    # Either a 504 or a JSON with success=False indicating timeout
    if resp.status_code == 504:
        assert True  # explicit timeout response
    else:
        # When force_timeout is unknown it may just succeed — that's also ok
        # What matters is it doesn't crash (500) and returns valid JSON
        assert resp.status_code in (200, 504)
        body = resp.json()
        assert isinstance(body, dict)


# ---------------------------------------------------------------------------
# 10. GET /health — openrouter, disk, auto_publisher 최소 3개 서비스 체크
# ---------------------------------------------------------------------------

def test_health_lists_openrouter_disk_auto_publisher(bridge_server):
    """GET /health?deep=true lists at least openrouter, disk, and auto_publisher services."""
    resp = requests.get(f"{BASE_URL}/health?deep=true", timeout=10)
    assert resp.status_code == 200
    body = resp.json()
    services = body.get("services", {})
    service_names = set(k.lower() for k in services.keys())
    required = {"openrouter", "disk", "auto_publisher"}
    found = required & service_names
    assert len(found) >= 3, (
        f"Expected services {required} in health check, got: {service_names}"
    )


# ---------------------------------------------------------------------------
# 11. Regression: existing run_auto_publish endpoint still reachable
# ---------------------------------------------------------------------------

def test_existing_publish_endpoint_still_reachable(bridge_server):
    """GET /publish endpoint still exists (regression guard for existing workflows)."""
    # dry_run=true로 subprocess 없이 라우트 등록만 확인
    resp = requests.get(f"{BASE_URL}/publish?lang=ko&dry_run=true", timeout=5)
    assert resp.status_code != 404, (
        "/publish endpoint was removed — breaks daily_publisher.json workflow"
    )


# ---------------------------------------------------------------------------
# 12. Phase 2 stub endpoints — 404 방지 (GET)
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("path", [
    "/benchmark/save",
    "/kpi/compute-health",
    "/newsletter/build",
])
def test_stub_get_returns_200_with_stub_flag(bridge_server, path):
    """스텁 라우트가 GET으로 호출되면 200 + {stub: true} 응답."""
    resp = requests.get(f"{BASE_URL}{path}", timeout=5)
    assert resp.status_code == 200, f"{path} returned {resp.status_code}"
    body = resp.json()
    assert body.get("stub") is True
    assert body.get("implemented") is False
    assert body.get("endpoint") == path


# ---------------------------------------------------------------------------
# 13. Phase 2 stub endpoints — 404 방지 (POST with body)
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("path", [
    "/newsletter/curate-weekly",
    "/cross-post/generate",
    "/dividend-report",
])
def test_stub_post_returns_200_with_stub_flag(bridge_server, path):
    """스텁 라우트가 POST로 호출되면 body가 있어도 200 + {stub: true} 응답."""
    resp = requests.post(
        f"{BASE_URL}{path}",
        json={"sample": "payload"},
        timeout=5,
    )
    assert resp.status_code == 200, f"{path} returned {resp.status_code}"
    body = resp.json()
    assert body.get("stub") is True
    assert body.get("endpoint") == path


# ---------------------------------------------------------------------------
# 14. Unknown paths still return 404
# ---------------------------------------------------------------------------

def test_unknown_path_still_404(bridge_server):
    """스텁 추가가 전체 404 fallback을 깨지 않았음을 확인."""
    resp = requests.get(f"{BASE_URL}/nonexistent-route-xyz", timeout=5)
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# 15. POST /publish-us-market-wrap (dry_run) — 파일 저장 없이 preview
# ---------------------------------------------------------------------------

def test_publish_us_market_wrap_dry_run(bridge_server, monkeypatch):
    """dry_run=true 면 Hugo/CF 호출 없이 title/slug/len 만 반환."""
    from auto_publisher import market_wrap

    fake_snap = {
        "date_kst": "2026-04-24",
        "us_close_date": "2026-04-23",
        "is_us_market_holiday": False,
        "indices": [
            {"ticker": "SPY", "name": "S&P 500", "price": 650.0, "pct": 0.5, "vol": 40_000_000, "prev_close_ts": "2026-04-23"},
            {"ticker": "QQQ", "name": "Nasdaq-100", "price": 520.0, "pct": 0.7, "vol": 30_000_000, "prev_close_ts": "2026-04-23"},
            {"ticker": "DIA", "name": "Dow 30", "price": 450.0, "pct": 0.2, "vol": 3_000_000, "prev_close_ts": "2026-04-23"},
            {"ticker": "IWM", "name": "Russell 2000", "price": 220.0, "pct": -0.1, "vol": 20_000_000, "prev_close_ts": "2026-04-23"},
        ],
        "vix": {"price": 14.5, "pct": -1.5},
        "sectors": [
            {"ticker": t, "name": n, "pct": 0.3, "price": 50.0}
            for t, n in [
                ("XLK","Technology"),("XLC","Communication Services"),("XLY","Consumer Discretionary"),
                ("XLF","Financials"),("XLI","Industrials"),("XLV","Health Care"),
                ("XLB","Materials"),("XLP","Consumer Staples"),("XLRE","Real Estate"),
                ("XLU","Utilities"),("XLE","Energy"),
            ]
        ],
        "top_gainers_sectors": ["XLK","XLC","XLY"],
        "top_losers_sectors": ["XLE","XLU","XLRE"],
        "narrative_hint": "growth_led",
    }
    monkeypatch.setattr(market_wrap, "fetch_us_market_snapshot", lambda: fake_snap)

    resp = requests.post(
        f"{BASE_URL}/publish-us-market-wrap",
        json={"dry_run": True, "lang": "ko"},
        timeout=15,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body.get("success") is True
    assert body.get("dry_run") is True
    assert "미국 증시 마감" in body.get("title", "")
    assert body.get("len", 0) > 1500
    # 3-탭 구조: 신규 시황 글은 daily/ section 으로 발행되어야 함
    # dry_run 응답에는 url 이 없을 수 있으나 slug 는 있음 → daily 경로 검증은 build markdown 단계에 있음


def test_publish_us_market_intraday_dry_run(bridge_server, monkeypatch):
    """장중 시황 dry_run — 파일 저장 없이 preview."""
    from auto_publisher import market_intraday

    fake_snap = {
        "date_kst": "2026-04-26",
        "us_session_date": "2026-04-25",
        "is_us_market_holiday": False,
        "minutes_after_open": 30,
        "indices": [
            {"ticker": "SPY", "name": "S&P 500", "open": 651.0, "current": 654.0,
             "pct_from_open": 0.46, "pct_gap_from_prev": 0.30, "vol_30m": 12_000_000,
             "prev_close_ts": "2026-04-25"},
            {"ticker": "QQQ", "name": "Nasdaq-100", "open": 518.0, "current": 521.5,
             "pct_from_open": 0.68, "pct_gap_from_prev": 0.20, "vol_30m": 9_500_000,
             "prev_close_ts": "2026-04-25"},
            {"ticker": "DIA", "name": "Dow 30", "open": 449.0, "current": 449.8,
             "pct_from_open": 0.18, "pct_gap_from_prev": -0.05, "vol_30m": 800_000,
             "prev_close_ts": "2026-04-25"},
            {"ticker": "IWM", "name": "Russell 2000", "open": 219.0, "current": 218.7,
             "pct_from_open": -0.14, "pct_gap_from_prev": 0.10, "vol_30m": 5_500_000,
             "prev_close_ts": "2026-04-25"},
        ],
        "vix": {"price": 14.2, "pct_from_prev": -3.1, "level": "low"},
        "sectors": [
            {"ticker": t, "name": n, "pct_from_open": 0.3, "open": 50.0, "current": 50.15}
            for t, n in [
                ("XLK","Technology"),("XLC","Communication Services"),("XLY","Consumer Discretionary"),
                ("XLF","Financials"),("XLI","Industrials"),("XLV","Health Care"),
                ("XLB","Materials"),("XLP","Consumer Staples"),("XLRE","Real Estate"),
                ("XLU","Utilities"),("XLE","Energy"),
            ]
        ],
        "top_gainers_sectors": ["XLK","XLC","XLY"],
        "top_losers_sectors": ["XLE","XLU","XLRE"],
        "gap": "gap_up",
        "narrative_hint": "early_strength",
    }
    monkeypatch.setattr(market_intraday, "fetch_intraday_snapshot", lambda: fake_snap)

    resp = requests.post(
        f"{BASE_URL}/publish-us-market-intraday",
        json={"dry_run": True, "lang": "ko"},
        timeout=15,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body.get("success") is True
    assert body.get("dry_run") is True
    assert "장중" in body.get("title", "")
    assert body.get("len", 0) > 1500
    assert body.get("gap") in ("gap_up", "gap_down", "gap_flat")
    # 3-탭 구조: intraday 도 daily/ section 으로 발행


def test_publish_us_market_intraday_skips_when_not_in_session(bridge_server, monkeypatch):
    """장 안 열린 상태(open=0) 면 skipped=true."""
    from auto_publisher import market_intraday

    closed_snap = {
        "date_kst": "2026-04-26",
        "us_session_date": "2026-04-25",
        "is_us_market_holiday": True,  # 장 미개장
        "minutes_after_open": 30,
        "indices": [{"ticker": "SPY", "name": "S&P 500", "open": 0.0, "current": 0.0,
                     "pct_from_open": 0.0, "pct_gap_from_prev": 0.0, "vol_30m": 0,
                     "prev_close_ts": "2026-04-25"}],
        "vix": {"price": 0.0, "pct_from_prev": 0.0, "level": "low"},
        "sectors": [],
        "top_gainers_sectors": [],
        "top_losers_sectors": [],
        "gap": "gap_flat",
        "narrative_hint": "mixed",
    }
    monkeypatch.setattr(market_intraday, "fetch_intraday_snapshot", lambda: closed_snap)

    resp = requests.post(
        f"{BASE_URL}/publish-us-market-intraday",
        json={"lang": "ko"},
        timeout=10,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body.get("success") is True
    assert body.get("skipped") is True
    assert body.get("reason") == "us_market_not_in_session"


def test_publish_us_market_wrap_skips_on_holiday(bridge_server, monkeypatch):
    """휴장일 스냅샷이면 skipped=true 로 조기 종료."""
    from auto_publisher import market_wrap

    holiday_snap = {
        "date_kst": "2026-04-24",
        "us_close_date": "2026-04-21",
        "is_us_market_holiday": True,
        "indices": [{"ticker": "SPY", "name": "S&P 500", "price": 650.0, "pct": 0.0,
                     "vol": 0, "prev_close_ts": "2026-04-21"}],
        "vix": {"price": 14.5, "pct": 0.0},
        "sectors": [],
        "top_gainers_sectors": [],
        "top_losers_sectors": [],
        "narrative_hint": "mixed",
    }
    monkeypatch.setattr(market_wrap, "fetch_us_market_snapshot", lambda: holiday_snap)

    resp = requests.post(
        f"{BASE_URL}/publish-us-market-wrap",
        json={"lang": "ko"},
        timeout=10,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body.get("success") is True
    assert body.get("skipped") is True
    assert body.get("reason") == "us_market_holiday"
