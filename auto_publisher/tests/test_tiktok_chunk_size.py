"""TikTok upload chunk size 회귀 테스트.

배경: TikTok Content Posting API v2 의 init 엔드포인트는
다음 invariant 를 강제:
- chunk_size 는 file_size 보다 클 수 없음
- 5MB 미만 파일은 single chunk (chunk_size = file_size, total_chunk_count = 1)
- 5MB 이상 파일은 chunk_size 5MB ~ 64MB 범위
- chunk_size * (total_chunk_count - 1) + last_chunk_size = file_size

원래 버그 (cycle 22 이전):
- CHUNK_SIZE 가 10MB 로 하드코딩되어 1.26MB 파일도 chunk_size=10MB 로 init 요청
- TikTok 응답: 400 "The chunk size is invalid"

이 테스트는 _calc_chunk_params(file_size) 헬퍼의 invariant 를 잠근다.
"""

from __future__ import annotations

import pytest


# ── 1. 단위: _calc_chunk_params 헬퍼 ─────────────────────

def test_small_file_uses_single_chunk():
    """5MB 미만 파일은 single chunk, chunk_size = file_size."""
    from auto_publisher.video_uploader import _calc_chunk_params
    chunk_size, total = _calc_chunk_params(1_264_496)  # 1.26MB (실제 fallback_card 크기)
    assert chunk_size == 1_264_496, f"small file chunk_size != file_size: {chunk_size}"
    assert total == 1, f"small file should be 1 chunk: {total}"


def test_5mb_threshold_exact():
    """정확히 5MB 파일: 1 chunk."""
    from auto_publisher.video_uploader import _calc_chunk_params
    file_size = 5 * 1024 * 1024
    chunk_size, total = _calc_chunk_params(file_size)
    assert chunk_size == file_size
    assert total == 1


def test_large_file_uses_10mb_chunks():
    """10MB 이상 파일은 10MB chunk 로 분할."""
    from auto_publisher.video_uploader import _calc_chunk_params
    file_size = 25 * 1024 * 1024  # 25MB
    chunk_size, total = _calc_chunk_params(file_size)
    assert chunk_size == 10 * 1024 * 1024
    assert total == 3  # 10 + 10 + 5


def test_chunk_size_invariants_hold_for_any_size():
    """모든 크기에 대해 TikTok invariant 가 지켜진다."""
    from auto_publisher.video_uploader import _calc_chunk_params
    for size in [
        1024,                  # 1KB (극소)
        100_000,               # 100KB
        1_000_000,             # 1MB
        1_264_496,             # 실제 1.26MB
        5_000_000,             # 4.77MB (5MB 미만)
        5_242_880,             # 정확히 5MB
        10_000_000,            # 9.5MB
        15 * 1024 * 1024,      # 15MB
        100 * 1024 * 1024,     # 100MB
        500 * 1024 * 1024,     # 500MB
    ]:
        chunk_size, total = _calc_chunk_params(size)
        # invariant 1: chunk_size 는 file_size 보다 크지 않다
        assert chunk_size <= size, f"size={size}: chunk_size {chunk_size} > file_size"
        # invariant 2: total >= 1
        assert total >= 1, f"size={size}: total < 1"
        # invariant 3: chunk_size * total >= file_size (마지막 chunk 가 더 작을 수 있어 등호 허용)
        # 마지막 chunk 가 chunk_size 보다 작을 수 있으므로 ceil 관계
        import math
        assert math.ceil(size / chunk_size) == total, (
            f"size={size}: ceil({size}/{chunk_size})={math.ceil(size/chunk_size)} != total {total}"
        )
        # invariant 4: 5MB 미만 파일은 단일 chunk
        if size < 5 * 1024 * 1024:
            assert total == 1, f"size={size} < 5MB: total != 1"


# ── 2. init body 통합 ────────────────────────────────────

def test_init_body_for_small_file_is_valid(tmp_path, monkeypatch):
    """1.26MB 파일에 대한 init body 의 source_info 가 TikTok 규격을 만족."""
    from auto_publisher.video_uploader import _build_init_body

    # 가짜 mp4 (1.26MB) — TikTok 안 보내고 body 만 빌드
    fake = tmp_path / "small.mp4"
    fake.write_bytes(b"\x00" * 1_264_496)

    body = _build_init_body(
        video_path=fake,
        title="t",
        privacy="SELF_ONLY",
        disable_duet=False,
        disable_comment=False,
        disable_stitch=False,
    )
    src = body["source_info"]
    assert src["video_size"] == 1_264_496
    # 1.26MB 파일은 chunk_size = video_size 여야 함
    assert src["chunk_size"] == 1_264_496, (
        f"small file chunk_size 가 video_size 와 다름: {src['chunk_size']}"
    )
    assert src["total_chunk_count"] == 1
    assert src["source"] == "FILE_UPLOAD"
