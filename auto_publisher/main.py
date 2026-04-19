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
import sys

from auto_publisher.config import (
    TISTORY_BLOG_NAME,
    TISTORY_KAKAO_ID,
    TISTORY_KAKAO_PW,
    TISTORY_ENABLED,
    CONTENT_NICHE,
    LOG_FILE,
    validate_config,
)
from auto_publisher.content_generator import generate_blog_post
from auto_publisher.publishers.tistory import TistoryPublisher
from auto_publisher.publishers.hugo import HugoPublisher
from auto_publisher.topic_manager import TopicManager

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


def do_generate(topic_info: dict | None = None) -> dict | None:
    """콘텐츠 생성"""
    tm = TopicManager()

    if topic_info is None:
        topic_info = tm.get_next_topic()
        if topic_info is None:
            logger.error("발행할 토픽이 없습니다.")
            return None

    logger.info(f"콘텐츠 생성 시작: {topic_info['topic']}")

    post = generate_blog_post(
        topic=topic_info["topic"],
        keywords=topic_info["keywords"],
        niche=CONTENT_NICHE,
    )

    logger.info(f"콘텐츠 생성 완료: {post['title']} ({len(post['content_html'])}자)")
    return {"topic_info": topic_info, "post": post}


def do_publish(topic_info: dict | None = None) -> dict | None:
    """콘텐츠 생성 + 발행"""
    result = do_generate(topic_info)
    if result is None:
        return None

    topic_info = result["topic_info"]
    post = result["post"]
    tm = TopicManager()
    publish_results = {}

    # Hugo 발행 (마크다운 파일 저장 + 빌드)
    if HUGO_ENABLED:
        try:
            publisher = HugoPublisher()
            hugo_result = publisher.publish(
                title=post["title"],
                content_html=post["content_html"],
                tags=post.get("tags", []),
                meta_description=post.get("meta_description", ""),
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


def cmd_run(args):
    """즉시 생성 + 발행"""
    errors = validate_config()
    if errors:
        for e in errors:
            logger.error(e)
        print("\n설정 오류가 있습니다. .env 파일을 확인해주세요.")
        sys.exit(1)

    result = do_publish()
    if result:
        print(f"\n발행 완료!")
        print(f"  제목: {result['post']['title']}")
        for platform, pr in result["publish_results"].items():
            if "url" in pr:
                print(f"  {platform}: {pr['url']}")
            elif "error" in pr:
                print(f"  {platform}: 실패 — {pr['error']}")
    else:
        print("발행할 토픽이 없습니다.")


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


def main():
    parser = argparse.ArgumentParser(
        description="Auto Publisher Bot — 한국 투자 니치 콘텐츠 자동 발행",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    subparsers = parser.add_subparsers(dest="command", help="명령어")

    subparsers.add_parser("run", help="즉시 생성 + 발행")
    subparsers.add_parser("schedule", help="스케줄러 데몬 시작")
    subparsers.add_parser("generate", help="콘텐츠 생성만 (테스트)")
    subparsers.add_parser("test-login", help="Tistory 로그인 테스트")
    subparsers.add_parser("topics", help="토픽 큐 상태")
    subparsers.add_parser("history", help="발행 이력")

    args = parser.parse_args()

    commands = {
        "run": cmd_run,
        "schedule": cmd_schedule,
        "generate": cmd_generate,
        "test-login": cmd_test_login,
        "topics": cmd_topics,
        "history": cmd_history,
    }

    if args.command in commands:
        commands[args.command](args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
