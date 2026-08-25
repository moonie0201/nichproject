"""Tests for video_script quality improvements (Improvements 1 & 2)."""
import pytest
from auto_publisher import video_script


def test_strip_markup():
    """_strip_blog_markup should remove all markdown syntax."""
    raw = "## h2\n**bold**\n> quote\n[link](url)\n|table|col|"
    result = video_script._strip_blog_markup(raw)
    assert "#" not in result, f"heading marker found: {result!r}"
    assert "**" not in result, f"bold marker found: {result!r}"
    assert result.lstrip().startswith(">") is False, f"blockquote marker found: {result!r}"
    assert "[" not in result, f"link bracket found: {result!r}"
    assert "|" not in result, f"table pipe found: {result!r}"
    # the text content should survive
    assert "h2" in result
    assert "bold" in result
    assert "quote" in result
    assert "link" in result


def test_max_iter_default_3():
    """VIDEO_SCRIPT_MAX_ITER source-code default should be >= 3.
    We reload the module without the env override to check the true default."""
    import importlib
    import os
    import sys

    # Remove any env override so we see the coded default
    old_val = os.environ.pop("VIDEO_SCRIPT_MAX_ITER", None)
    try:
        # Force fresh module load without the env var
        mod_name = "auto_publisher.video_script"
        if mod_name in sys.modules:
            del sys.modules[mod_name]
        import auto_publisher.video_script as fresh_vs
        assert fresh_vs._VIDEO_SCRIPT_MAX_ITER >= 3
    finally:
        # Restore original env state
        if old_val is not None:
            os.environ["VIDEO_SCRIPT_MAX_ITER"] = old_val
        # Reload original module back
        if mod_name in sys.modules:
            del sys.modules[mod_name]
        importlib.import_module(mod_name)
