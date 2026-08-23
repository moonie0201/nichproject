"""bridge 테스트 공통 설정.

테스트는 운영 토글에 좌우되면 안 된다. `.adsense_review` 플래그가 켜져 있으면
발행 경로가 전부 no-op 이 되므로, 그 상태에서 발행 동작을 검증하는 테스트가
전부 깨진다. 여기서 플래그를 존재하지 않는 경로로 돌려 격리한다.

심사 모드 자체의 동작은 test_review_mode.py 에서 따로 검증한다.
"""

import pytest


@pytest.fixture(autouse=True)
def _disable_adsense_review_mode(monkeypatch, tmp_path):
    import n8n.bridge_api as api

    monkeypatch.setattr(api, "ADSENSE_REVIEW_FLAG", tmp_path / "no-such-flag")
