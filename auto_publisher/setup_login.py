"""
티스토리 로그인 세션 저장

Playwright 브라우저가 열리면 카카오 로그인 → 세션 자동 저장
"""

import time
from pathlib import Path
from playwright.sync_api import sync_playwright

SESSION_DIR = Path(__file__).parent / "data" / "tistory_session"
SESSION_FILE = SESSION_DIR / "state.json"
BLOG_NAME = "moonie"


def setup():
    SESSION_DIR.mkdir(parents=True, exist_ok=True)

    print("\n=== 티스토리 로그인 세션 저장 ===")
    print("브라우저가 열리면 카카오로 로그인해주세요.")
    print("로그인 완료되면 자동으로 저장됩니다. (최대 5분 대기)\n")

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=False,
            args=["--window-size=600,700", "--window-position=100,50"],
        )
        context = browser.new_context(
            user_agent="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
            viewport={"width": 580, "height": 650},
        )
        page = context.new_page()

        # 티스토리 로그인 페이지
        page.goto("https://www.tistory.com/auth/login", timeout=30000)
        print("✅ 브라우저 열림 — 카카오 로그인을 진행해주세요!")

        # 로그인 완료 대기 (5분)
        for i in range(300):
            time.sleep(1)
            try:
                url = page.url
            except Exception:
                continue

            if "tistory.com" in url and "auth/login" not in url and "accounts.kakao" not in url:
                print(f"\n🔑 로그인 감지! URL: {url}")
                break

            if i > 0 and i % 60 == 0:
                print(f"  ⏳ {i}초 경과... 로그인 대기 중")
        else:
            print("\n❌ 5분 타임아웃")
            browser.close()
            return

        # 관리 페이지 접근 확인
        time.sleep(2)
        page.goto(f"https://{BLOG_NAME}.tistory.com/manage", timeout=15000)
        time.sleep(3)

        if "/manage" in page.url and "login" not in page.url:
            context.storage_state(path=str(SESSION_FILE))
            print(f"✅ 세션 저장 완료: {SESSION_FILE}")
            print("\n🎉 이제 자동 발행이 가능합니다!")
        else:
            print(f"❌ 관리 페이지 접근 실패: {page.url}")

        browser.close()


if __name__ == "__main__":
    setup()
