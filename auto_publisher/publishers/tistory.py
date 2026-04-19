"""
Tistory 브라우저 자동화 발행 모듈 (Playwright)

API가 폐쇄되어 Playwright로 카카오 로그인 → 글쓰기 → 발행 자동화
"""

import json
import logging
import time
from pathlib import Path

from playwright.sync_api import sync_playwright, Browser, Page, TimeoutError as PWTimeout

logger = logging.getLogger(__name__)

# 로그인 세션 저장 경로
SESSION_DIR = Path(__file__).parent.parent / "data" / "tistory_session"


class TistoryPublisher:
    """Playwright 기반 Tistory 자동 발행"""

    def __init__(self, blog_name: str, kakao_id: str, kakao_pw: str, headless: bool = True):
        self.blog_name = blog_name
        self.kakao_id = kakao_id
        self.kakao_pw = kakao_pw
        self.headless = headless
        SESSION_DIR.mkdir(parents=True, exist_ok=True)

    def publish(
        self,
        title: str,
        content_html: str,
        tags: list[str] | None = None,
        category: str | None = None,
        visibility: str = "public",
    ) -> dict:
        """
        Tistory에 글 발행

        Args:
            title: 글 제목
            content_html: HTML 본문
            tags: 태그 목록
            category: 카테고리 이름 (None=기본)
            visibility: "public" 또는 "private"

        Returns:
            {"post_id": str, "url": str}
        """
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=self.headless)
            context = browser.new_context(
                storage_state=self._session_path() if self._session_path().exists() else None,
                user_agent="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
            )
            page = context.new_page()

            try:
                # 로그인 확인 / 실행
                self._ensure_login(page, context)

                # 글쓰기 페이지 이동
                write_url = f"https://{self.blog_name}.tistory.com/manage/newpost"
                page.goto(write_url, wait_until="domcontentloaded", timeout=30000)
                time.sleep(3)

                # 제목 입력
                self._set_title(page, title)

                # HTML 모드로 전환 후 본문 입력
                self._set_content_html(page, content_html)

                # 태그 입력
                if tags:
                    self._set_tags(page, tags)

                # 카테고리 설정
                if category:
                    self._set_category(page, category)

                # 공개/비공개 설정
                if visibility == "private":
                    self._set_private(page)

                # 발행 버튼 클릭
                result = self._click_publish(page)

                # 세션 저장
                context.storage_state(path=str(self._session_path()))
                logger.info(f"Tistory 발행 성공: {result.get('url', 'N/A')}")
                return result

            except Exception as e:
                # 디버그용 스크린샷
                screenshot_path = SESSION_DIR / "error_screenshot.png"
                try:
                    page.screenshot(path=str(screenshot_path))
                    logger.error(f"에러 스크린샷 저장: {screenshot_path}")
                except Exception:
                    pass
                logger.error(f"Tistory 발행 실패: {e}")
                raise
            finally:
                browser.close()

    def _session_path(self) -> Path:
        return SESSION_DIR / "state.json"

    def _ensure_login(self, page: Page, context):
        """로그인 상태 확인, 필요시 카카오 로그인"""
        page.goto(f"https://{self.blog_name}.tistory.com/manage", timeout=30000)
        time.sleep(2)

        # 이미 관리 페이지에 있으면 로그인됨
        if "/manage" in page.url and "login" not in page.url:
            logger.info("기존 세션으로 로그인 됨")
            return

        logger.info("카카오 로그인 시작")

        # 티스토리 로그인 페이지로 이동
        page.goto("https://www.tistory.com/auth/login", timeout=30000)
        time.sleep(2)

        # 카카오 로그인 버튼 클릭
        kakao_btn = page.locator("a.btn_login.link_kakao_id, a[href*='kakao']").first
        if kakao_btn.is_visible():
            kakao_btn.click()
            time.sleep(3)
        else:
            # 직접 카카오 로그인 페이지로
            page.goto("https://accounts.kakao.com/login?continue=https://www.tistory.com/auth/login/redirect?loginType=kakao", timeout=30000)
            time.sleep(2)

        # 카카오 로그인 폼
        self._kakao_login(page)

        # 로그인 후 관리 페이지 확인
        page.wait_for_url(f"**/{self.blog_name}.tistory.com/**", timeout=30000)
        time.sleep(2)

        # 세션 저장
        context.storage_state(path=str(self._session_path()))
        logger.info("카카오 로그인 성공, 세션 저장됨")

    def _kakao_login(self, page: Page):
        """카카오 계정 로그인"""
        try:
            # 이메일/비밀번호 입력
            email_input = page.locator("input[name='loginId'], input#loginId, input[name='email']").first
            email_input.wait_for(state="visible", timeout=10000)
            email_input.fill(self.kakao_id)

            pw_input = page.locator("input[name='password'], input#password").first
            pw_input.fill(self.kakao_pw)

            # 로그인 버튼
            login_btn = page.locator("button[type='submit'], button.btn_confirm").first
            login_btn.click()

            time.sleep(5)  # 로그인 처리 대기

            # 동의 화면이 나오면 동의
            try:
                agree_btn = page.locator("button:has-text('동의'), button:has-text('확인')").first
                if agree_btn.is_visible(timeout=3000):
                    agree_btn.click()
                    time.sleep(2)
            except PWTimeout:
                pass

        except PWTimeout as e:
            logger.error(f"카카오 로그인 폼을 찾을 수 없음: {e}")
            raise RuntimeError("카카오 로그인 실패 — 로그인 폼을 찾을 수 없습니다") from e

    def _set_title(self, page: Page, title: str):
        """제목 입력"""
        try:
            # 새 에디터 (React 기반)
            title_input = page.locator("#post-title-inp, .tit_post input, textarea.title").first
            title_input.wait_for(state="visible", timeout=10000)
            title_input.fill(title)
            logger.info(f"제목 입력 완료: {title[:50]}")
        except PWTimeout:
            # iframe 기반 에디터
            title_input = page.locator("input.txt_field, input[name='title']").first
            title_input.fill(title)

    def _set_content_html(self, page: Page, content_html: str):
        """HTML 모드로 본문 입력"""
        try:
            # HTML 모드 버튼 찾기
            html_btn = page.locator(
                "button:has-text('HTML'), "
                "button[data-mode='html'], "
                ".btn_html, "
                "a:has-text('HTML')"
            ).first

            if html_btn.is_visible(timeout=5000):
                html_btn.click()
                time.sleep(1)

            # HTML 에디터 영역에 입력
            # CodeMirror 기반
            code_editor = page.locator(".CodeMirror, .cm-editor, textarea.html").first
            if code_editor.is_visible(timeout=5000):
                # CodeMirror인 경우 클릭 후 키보드로 입력
                code_editor.click()
                page.keyboard.press("Control+a")
                time.sleep(0.3)
                # clipboard를 통한 붙여넣기가 더 안정적
                page.evaluate(f"""
                    (() => {{
                        const cm = document.querySelector('.CodeMirror');
                        if (cm && cm.CodeMirror) {{
                            cm.CodeMirror.setValue({json.dumps(content_html)});
                            return;
                        }}
                        // cm-editor (CodeMirror 6)
                        const cm6 = document.querySelector('.cm-editor');
                        if (cm6 && cm6.cmView) {{
                            cm6.cmView.view.dispatch({{
                                changes: {{from: 0, to: cm6.cmView.view.state.doc.length, insert: {json.dumps(content_html)}}}
                            }});
                            return;
                        }}
                        // textarea fallback
                        const ta = document.querySelector('textarea.html, textarea[name="content"]');
                        if (ta) {{
                            ta.value = {json.dumps(content_html)};
                            ta.dispatchEvent(new Event('input', {{bubbles: true}}));
                        }}
                    }})();
                """)
                logger.info(f"HTML 본문 입력 완료 ({len(content_html)}자)")
            else:
                # contenteditable div에 직접 입력
                editor = page.locator(
                    "[contenteditable='true'], "
                    ".mce-content-body, "
                    "#content, "
                    ".editor_content"
                ).first
                editor.wait_for(state="visible", timeout=10000)
                page.evaluate(f"""
                    (() => {{
                        const el = document.querySelector("[contenteditable='true']") ||
                                   document.querySelector('.mce-content-body') ||
                                   document.querySelector('#content');
                        if (el) el.innerHTML = {json.dumps(content_html)};
                    }})();
                """)
                logger.info(f"Rich 본문 입력 완료 ({len(content_html)}자)")

        except Exception as e:
            logger.error(f"본문 입력 실패: {e}")
            raise

    def _set_tags(self, page: Page, tags: list[str]):
        """태그 입력"""
        try:
            tag_input = page.locator(
                "input.tag_input, "
                "input[placeholder*='태그'], "
                "input[placeholder*='tag'], "
                ".tag-input input"
            ).first

            if not tag_input.is_visible(timeout=5000):
                logger.warning("태그 입력 필드를 찾을 수 없음, 건너뜀")
                return

            for tag in tags[:10]:  # 최대 10개
                tag_input.fill(tag)
                tag_input.press("Enter")
                time.sleep(0.3)

            logger.info(f"태그 입력 완료: {', '.join(tags[:10])}")
        except Exception as e:
            logger.warning(f"태그 입력 실패 (무시): {e}")

    def _set_category(self, page: Page, category: str):
        """카테고리 선택"""
        try:
            cat_select = page.locator(
                "select.category, "
                "select[name='category'], "
                "#category"
            ).first

            if cat_select.is_visible(timeout=3000):
                cat_select.select_option(label=category)
                logger.info(f"카테고리 설정: {category}")
            else:
                # 드롭다운 버튼 방식
                cat_btn = page.locator("button:has-text('카테고리'), .btn_category").first
                if cat_btn.is_visible(timeout=3000):
                    cat_btn.click()
                    time.sleep(1)
                    page.locator(f"text={category}").first.click()
                    logger.info(f"카테고리 설정: {category}")
        except Exception as e:
            logger.warning(f"카테고리 설정 실패 (무시): {e}")

    def _set_private(self, page: Page):
        """비공개 설정"""
        try:
            private_radio = page.locator(
                "input[value='0'], "
                "input[name='visibility'][value='0'], "
                "label:has-text('비공개')"
            ).first
            if private_radio.is_visible(timeout=3000):
                private_radio.click()
                logger.info("비공개 설정 완료")
        except Exception as e:
            logger.warning(f"비공개 설정 실패 (무시): {e}")

    def _click_publish(self, page: Page) -> dict:
        """발행 버튼 클릭 및 결과 반환"""
        time.sleep(2)

        # 발행 버튼 (다양한 셀렉터 시도)
        publish_btn = page.locator(
            "button:has-text('발행'), "
            "button:has-text('완료'), "
            "button:has-text('저장'), "
            "button.btn_publish, "
            "#publish-layer-btn, "
            ".btn_save"
        ).first

        publish_btn.wait_for(state="visible", timeout=10000)
        publish_btn.click()
        time.sleep(2)

        # 발행 확인 팝업이 있으면 한 번 더 클릭
        try:
            confirm_btn = page.locator(
                "button:has-text('발행'), "
                "button:has-text('확인'), "
                ".btn_ok"
            ).first
            if confirm_btn.is_visible(timeout=5000):
                confirm_btn.click()
                time.sleep(3)
        except PWTimeout:
            pass

        # 발행 후 URL 추출
        time.sleep(3)
        current_url = page.url

        # 포스트 ID 추출 시도
        post_id = "unknown"
        if self.blog_name in current_url:
            parts = current_url.rstrip("/").split("/")
            if parts and parts[-1].isdigit():
                post_id = parts[-1]

        post_url = current_url if post_id != "unknown" else f"https://{self.blog_name}.tistory.com"

        return {"post_id": post_id, "url": post_url}

    def test_login(self) -> bool:
        """로그인 테스트 (설정 확인용)"""
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=self.headless)
            context = browser.new_context(
                storage_state=self._session_path() if self._session_path().exists() else None,
                user_agent="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
            )
            page = context.new_page()

            try:
                self._ensure_login(page, context)
                logger.info("로그인 테스트 성공")
                return True
            except Exception as e:
                logger.error(f"로그인 테스트 실패: {e}")
                return False
            finally:
                browser.close()
