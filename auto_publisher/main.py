"""
Auto Publisher Bot — 메인 엔트리포인트

사용법:
    python -m auto_publisher.main run          # 즉시 생성 + 발행
    python -m auto_publisher.main schedule     # 스케줄러 데몬 시작
    python -m auto_publisher.main generate     # 콘텐츠 생성만 (발행 안 함)
    python -m auto_publisher.main setup-tistory # Tistory OAuth 설정
    python -m auto_publisher.main topics       # 토픽 큐 상태
    python -m auto_publisher.main history      # 발행 이력
"""

import argparse
import logging
import subprocess
import sys
from pathlib import Path

from auto_publisher.config import (
    TISTORY_BLOG_NAME,
    TISTORY_KAKAO_ID,
    TISTORY_KAKAO_PW,
    TISTORY_ENABLED,
    CONTENT_NICHE,
    LOG_FILE,
    SUPPORTED_LANGUAGES,
    validate_config,
)
from auto_publisher.content_generator import generate_blog_post, translate_post, CATEGORIES_BY_LANG
from auto_publisher.publishers.hugo import HugoPublisher
from auto_publisher.topic_manager import TopicManager
from auto_publisher.notifier import notify_discord
from auto_publisher.market_analyzer import LANG_TICKERS

HUGO_ENABLED = True

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger(__name__)

VIDEO_CONTENT_ROOT = Path("/home/mh/ocstorage/workspace/nichproject/web/content")
VIDEO_CONTENT_SECTIONS = ("blog", "study", "daily", "weekly")


def resolve_video_source(
    slug: str,
    lang: str = "ko",
    content_root: Path = VIDEO_CONTENT_ROOT,
) -> tuple[str, str, str] | None:
    """영상화할 slug의 실제 콘텐츠 파일과 URL을 찾는다."""
    for section in VIDEO_CONTENT_SECTIONS:
        md_path = Path(content_root) / lang / section / f"{slug}.md"
        if not md_path.is_file():
            continue
        return str(md_path), section, f"https://investiqs.net/{lang}/{section}/{slug}/"
    return None


def do_generate(topic_info: dict | None = None, lang: str = "ko") -> dict | None:
    """콘텐츠 생성"""
    tm = TopicManager(lang=lang)

    if topic_info is None:
        topic_info = tm.get_next_topic("blog")
        if topic_info is None:
            logger.error(f"[{lang}] 발행할 토픽이 없습니다.")
            return None

    logger.info(f"[{lang}] 콘텐츠 생성 시작: {topic_info['topic']}")

    try:
        post = generate_blog_post(
            topic=topic_info["topic"],
            keywords=topic_info["keywords"],
            lang=lang,
            category=topic_info.get("category", ""),
        )
    except Exception as e:
        logger.error(f"[{lang}] 생성 실패, 실패큐에 등록: {e}")
        tm.mark_failed(topic_info["id"], str(e)[:200])
        return None

    # 성공 시 실패큐에서 제거
    tm.clear_failed(topic_info["id"])

    logger.info(f"[{lang}] 콘텐츠 생성 완료: {post['title']} ({len(post['content_html'])}자)")
    return {"topic_info": topic_info, "post": post}


def do_publish(topic_info: dict | None = None, lang: str = "ko") -> dict | None:
    """콘텐츠 생성 + 발행"""
    result = do_generate(topic_info, lang=lang)
    if result is None:
        return None

    topic_info = result["topic_info"]
    post = result["post"]
    tm = TopicManager(lang=lang)
    publish_results = {}

    # Hugo 발행 (마크다운 파일 저장 + 빌드)
    if HUGO_ENABLED:
        try:
            publisher = HugoPublisher(lang=lang)
            hugo_result = publisher.publish(
                title=post["title"],
                content_html=post["content_html"],
                tags=post.get("tags", []),
                meta_description=post.get("meta_description", ""),
                categories=[topic_info.get("category", "재테크 기초"), "재테크"],
                primary_keyword=post.get("primary_keyword", ""),
                keywords_long_tail=post.get("keywords_long_tail", []),
                schema_faq=post.get("schema_faq", []),
                content_type=post.get("content_type", "guide"),
            )
            tm.mark_published(topic_info["id"], "hugo", hugo_result["filepath"])
            publish_results["hugo"] = hugo_result
            logger.info(f"Hugo 발행 완료: {hugo_result['filepath']}")
        except Exception as e:
            logger.error(f"Hugo 발행 실패: {e}", exc_info=True)
            publish_results["hugo"] = {"error": str(e)}

    # Tistory 발행 (Playwright 브라우저 자동화)
    if TISTORY_ENABLED:
        try:
            from auto_publisher.publishers.tistory import TistoryPublisher
            publisher = TistoryPublisher(
                blog_name=TISTORY_BLOG_NAME,
                kakao_id=TISTORY_KAKAO_ID,
                kakao_pw=TISTORY_KAKAO_PW,
            )
            tistory_result = publisher.publish(
                title=post["title"],
                content_html=post["content_html"],
                tags=post.get("tags", []),
            )
            tm.mark_published(topic_info["id"], "tistory", tistory_result["url"])
            publish_results["tistory"] = tistory_result
            logger.info(f"Tistory 발행 완료: {tistory_result['url']}")
        except Exception as e:
            logger.error(f"Tistory 발행 실패: {e}", exc_info=True)
            publish_results["tistory"] = {"error": str(e)}

    # 다른 플랫폼은 Phase 2/3에서 구현
    return {"topic_info": topic_info, "post": post, "publish_results": publish_results}


def do_analyze(ticker: str, lang: str = "ko") -> dict | None:
    """티커 분석 + 분석 포스트 생성 + Hugo 발행"""
    from auto_publisher.market_analyzer import run_analysis

    logger.info(f"[{lang}] {ticker} 분석 시작")
    try:
        analysis = run_analysis(ticker)
    except Exception as e:
        logger.error(f"[{ticker}] 분석 실패: {e}", exc_info=True)
        return None

    logger.info(f"[{ticker}] 신호: {analysis['final_action']}, 포스트 생성 중")
    try:
        from auto_publisher.content_generator import generate_analysis_post
    except ImportError:
        logger.error("generate_analysis_post 없음 — content_generator.py 확인 필요")
        return None
    post = generate_analysis_post(ticker=ticker, analysis=analysis, lang=lang)

    publisher = HugoPublisher(lang=lang, section="blog")
    hugo_result = publisher.publish(
        title=post["title"],
        content_html=post["content_html"],
        tags=post.get("tags", []),
        meta_description=post.get("meta_description", ""),
        categories=["시장분석", "AI분석"],
        primary_keyword=post.get("primary_keyword", ticker),
        keywords_long_tail=post.get("keywords_long_tail", []),
        schema_faq=post.get("schema_faq", []),
        content_type="analysis",
        ticker=ticker,
        mkt_data=analysis.get("mkt_data"),
    )
    logger.info(f"Hugo 분석 포스트 발행: {hugo_result['filepath']}")

    # 예측 신호 기록 (60일 후 자동 검증용)
    from datetime import date as _date
    from auto_publisher.prediction_tracker import PredictionTracker
    try:
        mkt = analysis.get("mkt_data", {}) or {}
        price = mkt.get("current_price")
        if price:
            _tracker = PredictionTracker()
            _tracker.record(
                slug=hugo_result.get("slug", ticker),
                ticker=ticker,
                signal=analysis["final_action"],
                price_at_publish=float(price),
                published_at=_date.today().isoformat(),
            )
            _tracker.export_json()
            logger.info(f"[{ticker}] 예측 기록: {analysis['final_action']} @ {price}")
    except Exception as e:
        logger.warning(f"예측 기록 실패 (무시): {e}")

    notify_discord(
        title=post["title"],
        url=hugo_result["url"],
        ticker=ticker,
        signal=analysis["final_action"],
        description=post.get("meta_description", ""),
        lang=lang,
        post_type="analysis",
    )

    return {
        "ticker": ticker,
        "final_action": analysis["final_action"],
        "post": post,
        "hugo": hugo_result,
    }


def _validate_video_file(path: str, expected_duration_sec: float,
                         expected_aspect: str = "16:9") -> dict:
    """ffprobe로 생성된 mp4 검증. ok=False 시 issues 목록 반환."""
    import json as _json
    probe = subprocess.run(
        ["ffprobe", "-v", "quiet", "-print_format", "json",
         "-show_streams", "-show_format", str(path)],
        capture_output=True, text=True, timeout=30,
    )
    if probe.returncode != 0:
        return {"ok": False, "issues": ["ffprobe_failed"]}
    data = _json.loads(probe.stdout)
    streams = data.get("streams", [])
    video = next((s for s in streams if s["codec_type"] == "video"), None)
    audio = next((s for s in streams if s["codec_type"] == "audio"), None)
    issues = []
    if not video:
        issues.append("no_video_stream")
    if not audio:
        issues.append("no_audio_stream")
    if video:
        w, h = video.get("width", 0), video.get("height", 0)
        if expected_aspect == "16:9" and not (w >= 1920 and h >= 1080):
            issues.append(f"low_resolution_{w}x{h}")
        elif expected_aspect == "9:16" and not (w >= 1080 and h >= 1920):
            issues.append(f"low_resolution_shorts_{w}x{h}")
    duration = float(data.get("format", {}).get("duration", 0))
    if expected_duration_sec > 0 and abs(duration - expected_duration_sec) > expected_duration_sec * 0.15:
        issues.append(f"duration_mismatch_expected_{expected_duration_sec:.0f}s_got_{duration:.0f}s")
    return {
        "ok": len(issues) == 0,
        "issues": issues,
        "duration": duration,
        "resolution": f"{video.get('width')}x{video.get('height')}" if video else None,
    }


def do_make_video(slug: str, lang: str = "ko",
                  upload: bool = True, privacy: str = "public") -> dict | None:
    """블로그 slug → 롱폼 + 쇼츠 영상 생성 + YouTube 업로드"""
    from pathlib import Path
    from auto_publisher.video_script import (
        build_video_data_pack, generate_long_video_script, generate_short_video_script, script_to_plain_text
    )
    from auto_publisher.video_tts import synthesize_tts_with_srt
    from auto_publisher.video_composer import compose_video

    source = resolve_video_source(slug=slug, lang=lang)
    if source is None:
        logger.error(f"영상 원본 파일 없음: slug={slug}, lang={lang}, sections={VIDEO_CONTENT_SECTIONS}")
        return None
    blog_md = Path(source[0])
    content_section = source[1]
    blog_url = source[2]

    cache_dir = Path(f"/home/mh/ocstorage/workspace/nichproject/.omc/video_cache/{slug}")
    cache_dir.mkdir(parents=True, exist_ok=True)
    results = {
        "slug": slug,
        "lang": lang,
        "blog_url": blog_url,
        "section": content_section,
        "source_path": str(blog_md),
    }

    # 블로그 파일에서 실제 존재하는 차트 경로 추출 (LLM 할루시네이션 방지용 원본)
    from auto_publisher.video_script import _extract_blog_text
    from auto_publisher.video_composer import _resolve_chart_path
    _title, _body, blog_chart_paths = _extract_blog_text(blog_md)
    video_data_pack = build_video_data_pack(blog_md, blog_url=blog_url)
    authoritative_charts = []
    for c in blog_chart_paths:
        p = _resolve_chart_path(c)
        if p and Path(p).exists():
            authoritative_charts.append(c)
    logger.info(f"블로그 실제 차트 {len(authoritative_charts)}개: {authoritative_charts}")

    # ─── 1) 롱폼 ───
    logger.info(f"[{slug}] 롱폼 대사 생성 시작")
    long_script = generate_long_video_script(blog_md, lang, blog_url=blog_url, data_pack=video_data_pack)
    long_text = script_to_plain_text(long_script)
    if not long_text:
        logger.error("롱폼 대사 비어있음")
        return None

    long_mp3 = cache_dir / "long.mp3"
    long_srt = cache_dir / "long.srt"
    tts_info = synthesize_tts_with_srt(long_text, lang, long_mp3, long_srt)

    # 롱폼 차트: 블로그 실제 차트 우선 + LLM 지정 차트 중 유효한 것만 추가
    llm_long_charts = [c.get("chart") for c in long_script.get("chapters", []) if c.get("chart")]
    valid_llm_long = [c for c in llm_long_charts
                      if _resolve_chart_path(c) and Path(_resolve_chart_path(c)).exists()]
    long_charts = authoritative_charts + [c for c in valid_llm_long if c not in authoritative_charts]
    if not long_charts:
        logger.warning(f"[{slug}] 블로그에 차트 없음 — fallback 카드 비주얼로 합성")
    long_mp4 = cache_dir / "long.mp4"
    if not compose_video(slug=f"{slug}_long",
                         audio_path=long_mp3, srt_path=long_srt,
                         chart_paths=long_charts,
                         audio_duration_sec=tts_info["duration_sec"],
                         out_path=long_mp4, aspect="16:9",
                         fallback_visual_plan=long_script.get("fallback_visual_plan"),
                         visual_beats=long_script.get("visual_beats"),
                         source_data_points=long_script.get("source_data_points")):
        logger.error("롱폼 영상 합성 실패")
        return None
    vq = _validate_video_file(long_mp4, tts_info["duration_sec"], "16:9")
    if not vq["ok"]:
        logger.warning(f"롱폼 품질 검증 실패: {vq['issues']}")
    results["long_mp4"] = str(long_mp4)
    results["long_duration_sec"] = tts_info["duration_sec"]
    results["long_video_quality"] = vq

    # 업로드
    if upload:
        try:
            from auto_publisher.video_uploader import upload_youtube
            up = upload_youtube(
                video_path=long_mp4,
                title=long_script["title"],
                description=long_script.get("description", "") + f"\n\n원본 블로그: {blog_url}",
                tags=long_script.get("tags", []),
                is_short=False, privacy=privacy,
            )
            results["long_youtube"] = up
        except Exception as e:
            logger.error(f"롱폼 업로드 실패: {e}")
            results["long_upload_error"] = str(e)

    # ─── 2) 쇼츠 (롱폼 압축) ───
    long_url = results.get("long_youtube", {}).get("url", blog_url)
    logger.info(f"[{slug}] 쇼츠 대사 생성 시작")
    short_script = generate_short_video_script(long_script, long_url, lang, data_pack=video_data_pack)
    short_text = script_to_plain_text(short_script)

    short_mp3 = cache_dir / "short.mp3"
    short_srt = cache_dir / "short.srt"
    tts_info_s = synthesize_tts_with_srt(short_text, lang, short_mp3, short_srt)

    # 쇼츠 차트: 블로그의 실제 차트 중 대표 1~2개 (롱폼과 동일 원본 사용)
    short_charts = authoritative_charts[:2] if authoritative_charts else long_charts[:2]
    logger.info(f"쇼츠 차트 {len(short_charts)}개: {short_charts}")
    short_mp4 = cache_dir / "short.mp4"
    if not compose_video(slug=f"{slug}_short",
                         audio_path=short_mp3, srt_path=short_srt,
                         chart_paths=short_charts,
                         audio_duration_sec=tts_info_s["duration_sec"],
                         out_path=short_mp4, aspect="9:16",
                         fallback_visual_plan=short_script.get("fallback_visual_plan"),
                         visual_beats=short_script.get("visual_beats"),
                         source_data_points=short_script.get("source_data_points")):
        logger.error("쇼츠 영상 합성 실패")
    else:
        vq_s = _validate_video_file(short_mp4, tts_info_s["duration_sec"], "9:16")
        if not vq_s["ok"]:
            logger.warning(f"쇼츠 품질 검증 실패: {vq_s['issues']}")
        results["short_mp4"] = str(short_mp4)
        results["short_duration_sec"] = tts_info_s["duration_sec"]
        results["short_video_quality"] = vq_s
        if upload:
            try:
                from auto_publisher.video_uploader import upload_youtube
                up = upload_youtube(
                    video_path=short_mp4,
                    title=short_script["title"],
                    description=short_script.get("description", "") + f"\n\n전체 영상: {long_url}",
                    tags=short_script.get("tags", []),
                    is_short=True, privacy=privacy,
                )
                results["short_youtube"] = up
            except Exception as e:
                logger.error(f"쇼츠 업로드 실패: {e}")
                results["short_upload_error"] = str(e)

    # Discord 알림
    try:
        long_url_final = results.get("long_youtube", {}).get("url", "")
        short_url_final = results.get("short_youtube", {}).get("url", "")
        msg = f"📺 롱폼: {long_url_final or '업로드 X'}\n📱 쇼츠: {short_url_final or '업로드 X'}"
        notify_discord(
            title=f"[YouTube] {long_script['title'][:60]}",
            url=long_url_final or blog_url,
            description=msg,
            lang=lang, post_type="blog",
        )
    except Exception:
        pass

    return results


def cmd_make_video(args):
    """블로그 slug로 YouTube 영상 생성 + 업로드"""
    slug = args.slug
    lang = getattr(args, "lang", "ko")
    upload = not getattr(args, "no_upload", False)
    privacy = getattr(args, "privacy", "public")
    result = do_make_video(slug=slug, lang=lang, upload=upload, privacy=privacy)
    if result:
        print(f"\n[YouTube] 영상 생성 완료")
        if "long_youtube" in result:
            print(f"  롱폼: {result['long_youtube']['url']}")
        if "short_youtube" in result:
            print(f"  쇼츠: {result['short_youtube']['url']}")
        print(f"  로컬: {result.get('long_mp4', '-')}, {result.get('short_mp4', '-')}")
    else:
        print(f"[YouTube] 실패")
        sys.exit(1)


def cmd_analyze(args):
    """AI 분석 포스트 생성 + 발행"""
    langs = SUPPORTED_LANGUAGES if getattr(args, "all_langs", False) else [getattr(args, "lang", "ko")]

    for lang in langs:
        tickers = getattr(args, "ticker", None)
        if tickers:
            ticker_list = [tickers]
        elif getattr(args, "all_tickers", False):
            ticker_list = LANG_TICKERS.get(lang, ["VOO"])
        else:
            ticker_list = [LANG_TICKERS.get(lang, ["VOO"])[0]]

        for ticker in ticker_list:
            result = do_analyze(ticker=ticker, lang=lang)
            if result:
                print(f"\n[{lang}] {ticker} 분석 완료 — {result['final_action']}")
                print(f"  제목: {result['post']['title']}")
                print(f"  URL: {result['hugo']['url']}")
            else:
                print(f"[{lang}] {ticker} 분석 실패")


def cmd_run(args):
    """즉시 생성 + 발행"""
    errors = validate_config()
    if errors:
        for e in errors:
            logger.error(e)
        print("\n설정 오류가 있습니다. .env 파일을 확인해주세요.")
        sys.exit(1)

    langs = SUPPORTED_LANGUAGES if getattr(args, "all_langs", False) else [getattr(args, "lang", "ko")]

    for lang in langs:
        result = do_publish(lang=lang)
        if result:
            print(f"\n[{lang}] 발행 완료!")
            print(f"  제목: {result['post']['title']}")
            for platform, pr in result["publish_results"].items():
                if "url" in pr:
                    print(f"  {platform}: {pr['url']}")
                elif "error" in pr:
                    print(f"  {platform}: 실패 — {pr['error']}")
        else:
            print(f"[{lang}] 발행할 토픽이 없습니다.")


def cmd_schedule(args):
    """스케줄러 데몬 시작"""
    errors = validate_config()
    if errors:
        for e in errors:
            logger.error(e)
        print("\n설정 오류가 있습니다. .env 파일을 확인해주세요.")
        sys.exit(1)

    from auto_publisher.scheduler import start_scheduler
    start_scheduler()


def cmd_generate(args):
    """콘텐츠 생성만 (발행 안 함, 테스트용)"""
    if not validate_config():
        pass  # Gemini만 있으면 됨

    result = do_generate()
    if result:
        post = result["post"]
        print(f"\n{'='*60}")
        print(f"제목: {post['title']}")
        print(f"{'='*60}")
        print(f"메타: {post.get('meta_description', 'N/A')}")
        print(f"태그: {', '.join(post.get('tags', []))}")
        print(f"{'='*60}")
        print(post["content_html"][:2000])
        if len(post["content_html"]) > 2000:
            print(f"\n... (총 {len(post['content_html'])}자, 일부만 표시)")
        print(f"{'='*60}")
    else:
        print("생성할 토픽이 없습니다.")


def cmd_test_login(args):
    """Tistory 로그인 테스트"""
    print("\n=== Tistory 로그인 테스트 ===\n")

    if not TISTORY_KAKAO_ID or not TISTORY_KAKAO_PW or not TISTORY_BLOG_NAME:
        print(".env에 다음 값을 설정해주세요:")
        print("  TISTORY_BLOG_NAME=블로그주소 (xxx.tistory.com의 xxx)")
        print("  TISTORY_KAKAO_ID=카카오 이메일")
        print("  TISTORY_KAKAO_PW=카카오 비밀번호")
        return

    from auto_publisher.publishers.tistory import TistoryPublisher
    publisher = TistoryPublisher(
        blog_name=TISTORY_BLOG_NAME,
        kakao_id=TISTORY_KAKAO_ID,
        kakao_pw=TISTORY_KAKAO_PW,
        headless=False,  # 테스트시 브라우저 보이게
    )

    if publisher.test_login():
        print("✅ 로그인 성공! 세션이 저장되었습니다.")
        print("   이후 자동 발행 시 저장된 세션을 사용합니다.")
    else:
        print("❌ 로그인 실패. 카카오 계정 정보를 확인해주세요.")


def cmd_topics(args):
    """토픽 큐 상태 표시"""
    tm = TopicManager()
    status = tm.get_status()

    print(f"\n=== 토픽 큐 상태 ===")
    print(f"전체: {status['total']}개 | 발행됨: {status['published']}개 | 남은 토픽: {status['remaining']}개")
    print(f"\n카테고리별:")

    for cat, info in status["categories"].items():
        bar = "█" * info["remaining"] + "░" * info["published"]
        print(f"  {cat:12s} | {bar} | 남음 {info['remaining']}/{info['total']}")

    # 다음 토픽 미리보기
    next_topic = tm.get_next_topic()
    if next_topic:
        print(f"\n다음 발행 토픽:")
        print(f"  [{next_topic['category']}] {next_topic['topic']}")
        print(f"  키워드: {', '.join(next_topic['keywords'])}")


def cmd_history(args):
    """발행 이력 표시"""
    tm = TopicManager()
    history = tm.get_history()

    if not history:
        print("\n발행 이력이 없습니다.")
        return

    print(f"\n=== 발행 이력 ({len(history)}건) ===")
    for h in history[-20:]:  # 최근 20건
        print(f"  [{h['published_at'][:16]}] {h['platform']:8s} | {h['topic_id']:12s} | {h.get('url', 'N/A')}")


def do_translate_publish(source_lang: str = "ko", target_lang: str = "en",
                         source_topic_info: dict = None) -> dict | None:
    """ko 포스트 1개를 target_lang으로 번역+현지화하여 발행"""
    import re
    from pathlib import Path

    # 가장 최근 source_lang 포스트 찾기
    src_tm = TopicManager(lang=source_lang)
    src_history = src_tm.get_history()
    if not src_history:
        logger.error(f"[{source_lang}] 번역 원본 없음")
        return None

    # 가장 최근 발행된 포스트 파일 읽기
    latest = src_history[-1]
    src_filepath = Path(latest["url"])
    if not src_filepath.exists():
        logger.error(f"원본 파일 없음: {src_filepath}")
        return None

    src_text = src_filepath.read_text(encoding="utf-8")
    # frontmatter title 추출
    m = re.search(r'^title:\s*"(.+)"', src_text, re.MULTILINE)
    src_title = m.group(1) if m else "untitled"
    # body는 frontmatter 이후
    parts = src_text.split("---", 2)
    src_body = parts[2] if len(parts) >= 3 else src_text

    source_post = {"title": src_title, "content_html": src_body}

    logger.info(f"[{target_lang}] 번역 시작: {src_title}")
    try:
        translated = translate_post(source_post, source_lang, target_lang)
    except Exception as e:
        logger.error(f"번역 실패: {e}", exc_info=True)
        return None

    publisher = HugoPublisher(lang=target_lang)
    hugo_result = publisher.publish(
        title=translated["title"],
        content_html=translated["content_html"],
        tags=translated.get("tags", []),
        meta_description=translated.get("meta_description", ""),
        categories=translated.get("categories") or CATEGORIES_BY_LANG.get(target_lang, ["Investing", "Personal Finance"]),
        primary_keyword=translated.get("primary_keyword", ""),
        keywords_long_tail=translated.get("keywords_long_tail", []),
        schema_faq=translated.get("schema_faq", []),
        content_type=translated.get("content_type", "guide"),
    )
    logger.info(f"[{target_lang}] 번역 발행 완료: {hugo_result['filepath']}")
    notify_discord(translated["title"], hugo_result["url"], lang=target_lang)
    return hugo_result


def cmd_translate(args):
    do_translate_publish(source_lang=args.source_lang, target_lang=args.target_lang)


def main():
    parser = argparse.ArgumentParser(
        description="Auto Publisher Bot — 한국 투자 니치 콘텐츠 자동 발행",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    subparsers = parser.add_subparsers(dest="command", help="명령어")

    run_p = subparsers.add_parser("run", help="즉시 생성 + 발행")
    run_p.add_argument("--lang", default="ko", choices=SUPPORTED_LANGUAGES, help="발행 언어")
    run_p.add_argument("--all-langs", action="store_true", help="전체 언어 순차 발행")
    subparsers.add_parser("schedule", help="스케줄러 데몬 시작")
    subparsers.add_parser("generate", help="콘텐츠 생성만 (테스트)")
    subparsers.add_parser("test-login", help="Tistory 로그인 테스트")
    subparsers.add_parser("topics", help="토픽 큐 상태")
    subparsers.add_parser("history", help="발행 이력")
    analyze_p = subparsers.add_parser("analyze", help="AI 시장 분석 포스트 생성 + 발행")
    analyze_p.add_argument("--ticker", default=None, help="분석할 티커 (예: VOO)")
    analyze_p.add_argument("--lang", default="ko", choices=SUPPORTED_LANGUAGES, help="출력 언어")
    analyze_p.add_argument("--all-tickers", action="store_true", help="언어별 기본 티커 전체 분석")
    analyze_p.add_argument("--all-langs", action="store_true", help="전체 언어 순차 발행")

    p_trans = subparsers.add_parser("translate", help="ko 포스트를 다른 언어로 번역+현지화 발행")
    p_trans.add_argument("--from", dest="source_lang", default="ko")
    p_trans.add_argument("--to", dest="target_lang", required=True, choices=["en", "ja", "vi", "id"])

    p_video = subparsers.add_parser("make-video", help="블로그 → 롱폼+쇼츠 영상 생성 + YouTube 업로드")
    p_video.add_argument("--slug", required=True, help="블로그 파일명 (확장자 제외)")
    p_video.add_argument("--lang", default="ko")
    p_video.add_argument("--no-upload", action="store_true", help="로컬 mp4만 생성, YouTube 업로드 스킵")
    p_video.add_argument("--privacy", default="public", choices=["public", "unlisted", "private"])

    args = parser.parse_args()

    commands = {
        "run": cmd_run,
        "schedule": cmd_schedule,
        "generate": cmd_generate,
        "test-login": cmd_test_login,
        "topics": cmd_topics,
        "history": cmd_history,
        "analyze": cmd_analyze,
        "translate": cmd_translate,
        "make-video": cmd_make_video,
    }

    if args.command in commands:
        commands[args.command](args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
