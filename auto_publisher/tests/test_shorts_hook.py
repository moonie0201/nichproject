"""쇼츠 첫 3초 임팩트 hook 생성기 회귀 테스트.

목적:
- TTS 첫 문장 (3초)이 시청자 retention 결정
- "ETF 운용보수 0.03% vs 0.5%" → "30년 후 5천만원이 사라진다"

ENV 토글:
- USE_SONNET_HOOK (default true)

설계:
- generate_hook(title, summary) → str (성공) | None (실패/disabled)
- Claude CLI 호출 (claude -p)
- JSON 응답 파싱 ({"hook": "..."})
- 실패 시 None (호출자가 원본 유지)
- 길이 제한 (default 35자)
"""
from __future__ import annotations
import json
from unittest.mock import patch, MagicMock
import pytest


def test_generate_hook_returns_short_string(monkeypatch):
    """정상 호출 → JSON 파싱 → hook 문자열."""
    monkeypatch.setenv("USE_SONNET_HOOK", "true")
    fake_run = MagicMock()
    fake_run.returncode = 0
    fake_run.stdout = '{"hook": "30년 후 5천만원이 사라진다"}'
    fake_run.stderr = ""
    from auto_publisher.shorts_hook import generate_hook
    with patch("subprocess.run", return_value=fake_run):
        result = generate_hook(title="ETF 운용보수 0.03% vs 0.5%",
                               summary="30년 복리 시뮬레이션 920만원 차이")
    assert isinstance(result, str)
    assert "5천만원" in result or "30년" in result


def test_generate_hook_disabled_returns_none(monkeypatch):
    """USE_SONNET_HOOK=false 면 None (호출자 fallback)."""
    monkeypatch.setenv("USE_SONNET_HOOK", "false")
    from auto_publisher.shorts_hook import generate_hook
    with patch("subprocess.run") as mock_run:
        result = generate_hook(title="X", summary="Y")
    assert result is None
    mock_run.assert_not_called()


def test_generate_hook_handles_codefence(monkeypatch):
    """LLM 응답에 코드펜스 있으면 제거 후 JSON 파싱."""
    monkeypatch.setenv("USE_SONNET_HOOK", "true")
    fake_run = MagicMock()
    fake_run.returncode = 0
    fake_run.stdout = '```json\n{"hook": "5천만원 격차"}\n```'
    fake_run.stderr = ""
    from auto_publisher.shorts_hook import generate_hook
    with patch("subprocess.run", return_value=fake_run):
        result = generate_hook(title="t", summary="s")
    assert result == "5천만원 격차"


def test_generate_hook_invalid_json_returns_none(monkeypatch):
    """JSON 파싱 실패 시 None (graceful)."""
    monkeypatch.setenv("USE_SONNET_HOOK", "true")
    fake_run = MagicMock()
    fake_run.returncode = 0
    fake_run.stdout = "not valid json at all"
    fake_run.stderr = ""
    from auto_publisher.shorts_hook import generate_hook
    with patch("subprocess.run", return_value=fake_run):
        result = generate_hook(title="t", summary="s")
    assert result is None


def test_generate_hook_subprocess_timeout_returns_none(monkeypatch):
    """CLI timeout 시 None."""
    monkeypatch.setenv("USE_SONNET_HOOK", "true")
    import subprocess
    from auto_publisher.shorts_hook import generate_hook
    with patch("subprocess.run", side_effect=subprocess.TimeoutExpired(cmd="claude", timeout=60)):
        result = generate_hook(title="t", summary="s")
    assert result is None


def test_generate_hook_truncates_too_long_response(monkeypatch):
    """응답이 너무 길면 max_chars 까지 자름."""
    monkeypatch.setenv("USE_SONNET_HOOK", "true")
    long_hook = "한국어 매우 긴 hook 문장으로 절대 35자 초과해야 함 정말 길게 길게 더 더"
    fake_run = MagicMock()
    fake_run.returncode = 0
    fake_run.stdout = json.dumps({"hook": long_hook}, ensure_ascii=False)
    fake_run.stderr = ""
    from auto_publisher.shorts_hook import generate_hook
    with patch("subprocess.run", return_value=fake_run):
        result = generate_hook(title="t", summary="s", max_chars=35)
    assert result is not None
    assert len(result) <= 35


def test_generate_hook_empty_or_whitespace_returns_none(monkeypatch):
    """빈 hook 또는 공백만 있으면 None."""
    monkeypatch.setenv("USE_SONNET_HOOK", "true")
    fake_run = MagicMock()
    fake_run.returncode = 0
    fake_run.stdout = '{"hook": "   "}'
    fake_run.stderr = ""
    from auto_publisher.shorts_hook import generate_hook
    with patch("subprocess.run", return_value=fake_run):
        result = generate_hook(title="t", summary="s")
    assert result is None
