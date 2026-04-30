import os
import pytest


def pytest_configure(config):
    config.addinivalue_line(
        "markers",
        "external_llm: marks tests that call real LLM endpoints (skip with -m 'not external_llm')",
    )


def pytest_collection_modifyitems(config, items):
    if os.getenv("CI") or os.getenv("SKIP_EXTERNAL_LLM"):
        skip = pytest.mark.skip(reason="external LLM disabled in CI/SKIP_EXTERNAL_LLM")
        for item in items:
            if item.get_closest_marker("external_llm"):
                item.add_marker(skip)
