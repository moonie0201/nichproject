"""hugo.toml 의 언어 설정이 파이썬 쪽 정책과 어긋나지 않는지 확인.

두 곳에 같은 사실이 적혀 있다:
  - auto_publisher/config.py  : SUPPORTED_LANGUAGES / RETIRED_LANGUAGES (발행 차단)
  - web/hugo.toml             : languages.X.disabled          (빌드 차단)

파이썬만 고치고 hugo 를 안 고쳐서, 은퇴한 ja/vi/id 가 계속 빌드되고 있었다.
축소 overlay(hugo.adsense.toml)가 그걸 가려주고 있었는데, overlay 는
심사 모드에서만 얹히므로 `.adsense_review` 를 지우는 순간 2,410 페이지가
조용히 되살아나는 상태였다.
"""

import re
import tomllib
from pathlib import Path

import pytest

from auto_publisher.config import RETIRED_LANGUAGES, SUPPORTED_LANGUAGES

_WEB = Path(__file__).resolve().parents[2] / "web"
_HUGO = _WEB / "hugo.toml"
_OVERLAY = _WEB / "hugo.adsense.toml"


def _languages(path: Path) -> dict:
    with path.open("rb") as fh:
        return tomllib.load(fh).get("languages", {})


@pytest.mark.parametrize("lang", RETIRED_LANGUAGES)
def test_retired_language_is_disabled_in_hugo(lang):
    """은퇴 언어는 overlay 없이 빌드해도 나오면 안 된다."""
    cfg = _languages(_HUGO).get(lang)
    assert cfg is not None, f"hugo.toml 에 {lang} 블록이 없다"
    assert cfg.get("disabled") is True, (
        f"{lang} 는 config.py 에서 은퇴했는데 hugo.toml 에서는 빌드된다. "
        "overlay 없이 빌드하면 그대로 되살아난다."
    )


@pytest.mark.parametrize("lang", SUPPORTED_LANGUAGES)
def test_supported_language_is_not_disabled_in_hugo(lang):
    """활성 언어를 hugo 에서 막아두면 심사 종료 후에도 안 살아난다."""
    cfg = _languages(_HUGO).get(lang, {})
    assert cfg.get("disabled") is not True, f"{lang} 는 활성 언어인데 hugo.toml 이 막고 있다"


def test_overlay_only_holds_review_scoped_settings():
    """overlay 에는 '심사 끝나면 되돌릴 것'만 남아야 한다.

    은퇴 언어를 overlay 에 두면 overlay 를 벗는 순간 되살아난다 —
    영구 결정은 hugo.toml 에 있어야 한다.
    """
    overlay_langs = _languages(_OVERLAY)
    leaked = sorted(set(overlay_langs) & set(RETIRED_LANGUAGES))
    assert not leaked, (
        f"은퇴 언어가 심사 overlay 에만 있다: {leaked}. hugo.toml 로 옮겨라."
    )


def test_overlay_ignorefiles_is_not_swallowed_by_languages_table():
    """TOML 스코프 함정 — ignoreFiles 가 [languages] 아래면 조용히 무시된다.

    실제로 한 번 당했다. 빌드는 성공하는데 아무것도 제외되지 않았다.
    """
    with _OVERLAY.open("rb") as fh:
        data = tomllib.load(fh)
    assert data.get("ignoreFiles"), "최상위 ignoreFiles 가 비었다 — [languages] 아래로 밀렸는지 확인"
    assert "ignoreFiles" not in data.get("languages", {}), \
        "ignoreFiles 가 languages 테이블 안으로 들어갔다 — [languages] 위로 올려라"


def test_overlay_ignorefiles_patterns_are_path_anchored():
    """hugo 의 ignoreFiles 는 파일 경로에 매칭된다. 앞뒤 구분자가 없으면 안 걸린다."""
    with _OVERLAY.open("rb") as fh:
        patterns = tomllib.load(fh)["ignoreFiles"]
    bad = [p for p in patterns if not (p.startswith("/") or p.startswith("'") or "/" in p)]
    assert not bad, f"경로 앵커가 없는 패턴: {bad}"
    for p in patterns:
        re.compile(p)          # 잘못된 정규식이면 여기서 터진다
