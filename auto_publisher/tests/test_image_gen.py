"""image_gen 테스트 — 백엔드 디스패치, env gate, 캐시."""
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from auto_publisher import image_gen


@pytest.fixture(autouse=True)
def isolated_out(tmp_path, monkeypatch):
    monkeypatch.setattr(image_gen, "WEB_STATIC_IMAGES", tmp_path)
    monkeypatch.setenv("IMAGE_GEN_ENABLED", "1")
    monkeypatch.setenv("IMAGE_GEN_MODEL", "z_image_turbo")


def test_disabled_returns_none(monkeypatch):
    monkeypatch.setenv("IMAGE_GEN_ENABLED", "0")
    assert image_gen.generate_cover_image("slug", "title") is None


def test_unknown_backend_falls_back_to_default(monkeypatch):
    monkeypatch.setenv("IMAGE_GEN_MODEL", "nonexistent_model")
    assert image_gen._selected_backend() == "z_image_turbo"


def test_supported_backends():
    assert "z_image_turbo" in image_gen.SUPPORTED_BACKENDS
    assert "flux_schnell" in image_gen.SUPPORTED_BACKENDS
    assert "qwen_image" in image_gen.SUPPORTED_BACKENDS


def test_prompt_has_visual_theme():
    """VOO/SPY 키워드 → stock market chart 테마 주입."""
    p = image_gen._build_prompt("VOO 5년 분석", "VOO", "ko")
    assert "stock market" in p or "chart" in p
    # 텍스트 부정문 포함
    assert "no letters" in p or "no text" in p

def test_prompt_dividend_theme():
    p = image_gen._build_prompt("SCHD 배당 분석", "SCHD", "ko")
    assert "coins" in p or "dividend" in p.lower() or "growth" in p


def test_generate_cover_dispatches_to_backend(monkeypatch, tmp_path):
    """선택한 backend 함수가 호출되는지."""
    mock_fn = MagicMock(side_effect=lambda prompt, out, **kw: out.write_bytes(b"x" * 2048))
    monkeypatch.setitem(image_gen._BACKENDS, "z_image_turbo", mock_fn)

    result = image_gen.generate_cover_image(
        slug="test-slug", title="테스트 제목", primary_keyword="VOO"
    )
    assert result is not None
    assert "cover-ai.png" in result
    assert mock_fn.called


def test_cache_hit_skips_regeneration(monkeypatch, tmp_path):
    """기존 cover-ai.png가 있으면 backend 호출 안 함."""
    cover = tmp_path / "test-slug" / "cover-ai.png"
    cover.parent.mkdir(parents=True)
    cover.write_bytes(b"cached")

    mock_fn = MagicMock()
    monkeypatch.setitem(image_gen._BACKENDS, "z_image_turbo", mock_fn)

    result = image_gen.generate_cover_image(slug="test-slug", title="x", primary_keyword="VOO")
    assert result is not None
    assert mock_fn.called is False  # 캐시 hit


def test_force_regen_bypasses_cache(monkeypatch, tmp_path):
    cover = tmp_path / "test-slug" / "cover-ai.png"
    cover.parent.mkdir(parents=True)
    cover.write_bytes(b"old")

    mock_fn = MagicMock(side_effect=lambda prompt, out, **kw: out.write_bytes(b"new-content"))
    monkeypatch.setitem(image_gen._BACKENDS, "z_image_turbo", mock_fn)

    result = image_gen.generate_cover_image(
        slug="test-slug", title="x", primary_keyword="VOO", force_regen=True
    )
    assert mock_fn.called
    assert cover.read_bytes() == b"new-content"


def test_backend_failure_returns_none(monkeypatch):
    def fail(*a, **k): raise RuntimeError("OOM")
    monkeypatch.setitem(image_gen._BACKENDS, "z_image_turbo", fail)
    result = image_gen.generate_cover_image(slug="x", title="t", primary_keyword="VOO")
    assert result is None


def test_explicit_backend_override(monkeypatch, tmp_path):
    mock_flux = MagicMock(side_effect=lambda prompt, out, **kw: out.write_bytes(b"x" * 2048))
    monkeypatch.setitem(image_gen._BACKENDS, "flux_schnell", mock_flux)

    result = image_gen.generate_cover_image(
        slug="t1", title="x", primary_keyword="VOO", backend="flux_schnell"
    )
    assert result is not None
    assert mock_flux.called


def test_slug_sanitization(monkeypatch, tmp_path):
    """위험 문자 포함 slug → 파일시스템 안전 변환."""
    mock_fn = MagicMock(side_effect=lambda prompt, out, **kw: out.write_bytes(b"x" * 2048))
    monkeypatch.setitem(image_gen._BACKENDS, "z_image_turbo", mock_fn)

    result = image_gen.generate_cover_image(
        slug="../../../etc/passwd", title="x", primary_keyword="VOO"
    )
    # 위로 escape 안 되어야 함
    assert ".." not in result
    assert "/etc/" not in result
