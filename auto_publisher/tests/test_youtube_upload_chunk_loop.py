"""YouTube upload_youtube — 청크 루프 cap 버그 회귀 테스트.

버그: max_retries=10 하드코딩으로 71MB 파일(15청크) 업로드 시
     10번째 청크(~70%)에서 RuntimeError 발생.
     "YouTube 업로드 실패: 청크 전송 최대 재시도 초과"

픽스: for 루프(max_retries=10) → while response is None 루프로 교체.
     실패 시에만 max_error_retries=5 카운트.
"""
from __future__ import annotations

import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock, call


def _make_chunk_responses(total_chunks: int):
    """total_chunks 개의 next_chunk() 반환값 시뮬레이션.
    마지막 호출만 response dict 반환, 나머지는 (status, None).
    """
    class FakeStatus:
        def __init__(self, progress):
            self._progress = progress
        def progress(self):
            return self._progress

    responses = []
    for i in range(total_chunks - 1):
        responses.append((FakeStatus((i + 1) / total_chunks), None))
    responses.append((None, {"id": "test_video_id", "status": {"uploadStatus": "uploaded"}}))
    return responses


def _mock_youtube_upload(tmp_path, file_size_mb: int, monkeypatch):
    """upload_youtube 내부 YouTube API를 모킹하여 청크 업로드 시뮬레이션."""
    from auto_publisher import video_uploader

    fake_video = tmp_path / "test.mp4"
    fake_video.write_bytes(b"\x00" * (file_size_mb * 1024 * 1024))

    chunk_size_bytes = 5 * 1024 * 1024
    total_chunks = -(-file_size_mb * 1024 * 1024 // chunk_size_bytes)  # ceiling div
    responses = _make_chunk_responses(total_chunks)
    response_iter = iter(responses)

    mock_request = MagicMock()
    mock_request.next_chunk.side_effect = lambda: next(response_iter)

    mock_youtube = MagicMock()
    mock_youtube.videos.return_value.insert.return_value = mock_request
    mock_youtube.thumbnails.return_value.set.return_value.execute.return_value = {}

    monkeypatch.setattr(video_uploader, "_load_credentials", lambda: MagicMock())

    return fake_video, mock_youtube, mock_request, total_chunks


def test_upload_71mb_shorts_completes(tmp_path, monkeypatch):
    """71MB 쇼츠(15청크)가 중단 없이 업로드 완료된다."""
    from auto_publisher import video_uploader

    fake_video, mock_youtube, mock_request, total_chunks = _mock_youtube_upload(
        tmp_path, file_size_mb=71, monkeypatch=monkeypatch
    )
    assert total_chunks == 15, f"71MB / 5MB = 15청크 기대: {total_chunks}"

    with patch("googleapiclient.discovery.build", return_value=mock_youtube):
        result = video_uploader.upload_youtube(
            fake_video,
            title="테스트 쇼츠 #Shorts",
            description="",
            is_short=True,
            privacy="public",
        )

    assert result["video_id"] == "test_video_id"
    assert mock_request.next_chunk.call_count == 15, (
        f"15번 next_chunk 호출 기대, 실제: {mock_request.next_chunk.call_count}"
    )


def test_upload_10mb_completes(tmp_path, monkeypatch):
    """10MB 파일(2청크)도 정상 완료."""
    from auto_publisher import video_uploader

    fake_video, mock_youtube, mock_request, total_chunks = _mock_youtube_upload(
        tmp_path, file_size_mb=10, monkeypatch=monkeypatch
    )

    with patch("googleapiclient.discovery.build", return_value=mock_youtube):
        result = video_uploader.upload_youtube(
            fake_video, title="10MB 테스트", description="", privacy="public"
        )

    assert result["video_id"] == "test_video_id"
    assert mock_request.next_chunk.call_count == total_chunks


def test_upload_retries_on_transient_error(tmp_path, monkeypatch):
    """일시적 네트워크 오류 시 재시도하고 결국 성공한다."""
    from auto_publisher import video_uploader

    fake_video = tmp_path / "test.mp4"
    fake_video.write_bytes(b"\x00" * (5 * 1024 * 1024))

    call_count = 0

    def flaky_next_chunk():
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            raise ConnectionError("일시적 네트워크 오류")
        return (None, {"id": "vid_ok", "status": {"uploadStatus": "uploaded"}})

    mock_request = MagicMock()
    mock_request.next_chunk.side_effect = flaky_next_chunk
    mock_youtube = MagicMock()
    mock_youtube.videos.return_value.insert.return_value = mock_request
    mock_youtube.thumbnails.return_value.set.return_value.execute.return_value = {}
    monkeypatch.setattr(video_uploader, "_load_credentials", lambda: MagicMock())

    with patch("googleapiclient.discovery.build", return_value=mock_youtube), \
         patch("time.sleep"):
        result = video_uploader.upload_youtube(
            fake_video, title="재시도 테스트", description="", privacy="public"
        )

    assert result["video_id"] == "vid_ok"
    assert call_count == 2


def test_upload_fails_after_max_error_retries(tmp_path, monkeypatch):
    """max_error_retries 초과 시 RuntimeError 발생."""
    from auto_publisher import video_uploader

    fake_video = tmp_path / "test.mp4"
    fake_video.write_bytes(b"\x00" * (5 * 1024 * 1024))

    mock_request = MagicMock()
    mock_request.next_chunk.side_effect = ConnectionError("영구 오류")
    mock_youtube = MagicMock()
    mock_youtube.videos.return_value.insert.return_value = mock_request
    monkeypatch.setattr(video_uploader, "_load_credentials", lambda: MagicMock())

    with patch("googleapiclient.discovery.build", return_value=mock_youtube), \
         patch("time.sleep"):
        with pytest.raises(RuntimeError, match="YouTube 업로드 실패"):
            video_uploader.upload_youtube(
                fake_video, title="실패 테스트", description="", privacy="public"
            )


def test_original_bug_10_chunk_cap_would_fail_71mb():
    """회귀: 구버전 for 루프 max=10 으로는 71MB(15청크) 업로드 불가 확인."""
    chunk_size = 5 * 1024 * 1024
    file_size = 71 * 1024 * 1024
    import math
    total_chunks = math.ceil(file_size / chunk_size)
    assert total_chunks > 10, (
        f"71MB 는 {total_chunks}청크 > 구버전 max_retries=10, 버그 재현 조건 성립"
    )
