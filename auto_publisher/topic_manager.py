"""
토픽 관리자 — 주제 큐 관리, 중복 방지, 발행 이력 추적
"""

import json
import logging
import uuid
from datetime import datetime
from pathlib import Path

from auto_publisher.config import (
    TOPICS_FILE,
    HISTORY_FILE,
    DATA_DIR,
    SUPPORTED_LANGUAGES,
)


class EventCalendar:
    """시즌 캘린더 자동화 (이벤트 기반 토픽 우선순위 조정)"""

    EVENTS = [
        {
            "month": 1,
            "day": 15,
            "name": "연말정산",
            "topic": "연말정산 소득공제 및 세액공제 최적화 전략",
            "keywords": ["연말정산", "세액공제", "소득공제"],
        },
        {
            "month": 5,
            "day": 1,
            "name": "종소세",
            "topic": "종합소득세 신고 가이드 및 절세 전략",
            "keywords": ["종합소득세", "절세", "세금신고"],
        },
        {
            "month": 3,
            "day": 15,
            "name": "FOMC",
            "topic": "FOMC 금리 결정과 투자 전략",
            "keywords": ["FOMC", "금리", "투자전략"],
        },
        {
            "month": 6,
            "day": 10,
            "name": "FOMC",
            "topic": "FOMC 금리 결정과 투자 전략",
            "keywords": ["FOMC", "금리", "투자전략"],
        },
        {
            "month": 9,
            "day": 15,
            "name": "FOMC",
            "topic": "FOMC 금리 결정과 투자 전략",
            "keywords": ["FOMC", "금리", "투자전략"],
        },
        {
            "month": 12,
            "day": 10,
            "name": "FOMC",
            "topic": "FOMC 금리 결정과 투자 전략",
            "keywords": ["FOMC", "금리", "투자전략"],
        },
        {
            "month": 12,
            "day": 20,
            "name": "배당락",
            "topic": "연말 배당락일 대비 투자 전략",
            "keywords": ["배당락", "배당투자", "연말투자"],
        },
    ]

    def get_upcoming_event(self) -> dict | None:
        """현재 날짜 D-3 이내의 이벤트를 찾음"""
        today = datetime.now()
        for event in self.EVENTS:
            event_date = datetime(today.year, event["month"], event["day"])
            delta = (event_date - today).days
            if 0 <= delta <= 3:
                return event
        return None


logger = logging.getLogger(__name__)

# 초기 토픽 목록 (50개 이상, 카테고리별 10개)
DEFAULT_TOPICS = [
    # === ETF (10) ===
    {
        "id": "etf-01",
        "topic": "ETF 초보자 가이드: 처음 시작하는 ETF 투자",
        "keywords": ["ETF", "ETF투자", "초보투자", "인덱스펀드"],
        "category": "ETF",
    },
    {
        "id": "etf-02",
        "topic": "미국 S&P500 ETF vs 국내 코스피 ETF 비교 분석",
        "keywords": ["S&P500", "코스피ETF", "해외ETF", "미국주식"],
        "category": "ETF",
    },
    {
        "id": "etf-03",
        "topic": "월배당 ETF로 매달 용돈 받는 법",
        "keywords": ["월배당ETF", "배당투자", "현금흐름", "패시브인컴"],
        "category": "ETF",
    },
    {
        "id": "etf-04",
        "topic": "2025년 유망 섹터 ETF 총정리",
        "keywords": ["섹터ETF", "반도체ETF", "AI ETF", "2025투자"],
        "category": "ETF",
    },
    {
        "id": "etf-05",
        "topic": "레버리지 ETF의 진실: 장기투자해도 될까?",
        "keywords": ["레버리지ETF", "곱버스", "인버스", "ETF위험"],
        "category": "ETF",
    },
    {
        "id": "etf-06",
        "topic": "ETF 수수료 비교: 운용보수가 수익률에 미치는 영향",
        "keywords": ["ETF수수료", "운용보수", "총보수", "비용비교"],
        "category": "ETF",
    },
    {
        "id": "etf-07",
        "topic": "금 ETF vs 실물 금: 어디에 투자할까?",
        "keywords": ["금ETF", "금투자", "실물금", "안전자산"],
        "category": "ETF",
    },
    {
        "id": "etf-08",
        "topic": "채권 ETF 완전정복: 금리 변동기 투자 전략",
        "keywords": ["채권ETF", "국채", "금리", "채권투자"],
        "category": "ETF",
    },
    {
        "id": "etf-09",
        "topic": "ETF 자동 적립식 투자: 매월 30만원으로 시작하기",
        "keywords": ["적립식투자", "ETF적립", "자동투자", "소액투자"],
        "category": "ETF",
    },
    {
        "id": "etf-10",
        "topic": "테마 ETF 투자 전 반드시 확인할 5가지",
        "keywords": ["테마ETF", "ETF선택", "투자체크리스트", "ETF분석"],
        "category": "ETF",
    },
    # === 배당주 (10) ===
    {
        "id": "div-01",
        "topic": "한국 고배당주 TOP 10: 안정적인 배당 수익 만들기",
        "keywords": ["고배당주", "배당수익률", "한국배당주", "배당킹"],
        "category": "배당주",
    },
    {
        "id": "div-02",
        "topic": "배당주 투자의 기초: 배당수익률과 배당성향 이해하기",
        "keywords": ["배당수익률", "배당성향", "배당기초", "주식배당"],
        "category": "배당주",
    },
    {
        "id": "div-03",
        "topic": "미국 배당 귀족주에 투자하는 방법",
        "keywords": ["배당귀족주", "미국배당주", "배당성장", "디비던드킹"],
        "category": "배당주",
    },
    {
        "id": "div-04",
        "topic": "배당금으로 월 100만원 만들기: 현실적인 로드맵",
        "keywords": ["배당금", "월배당", "배당생활", "경제적자유"],
        "category": "배당주",
    },
    {
        "id": "div-05",
        "topic": "배당주 vs 성장주: 나에게 맞는 투자 스타일은?",
        "keywords": ["배당주", "성장주", "투자스타일", "주식비교"],
        "category": "배당주",
    },
    {
        "id": "div-06",
        "topic": "배당락일 전후 주가 변화와 매매 전략",
        "keywords": ["배당락일", "배당기준일", "배당매매", "배당전략"],
        "category": "배당주",
    },
    {
        "id": "div-07",
        "topic": "리츠(REITs) 투자: 소액으로 건물주 되는 법",
        "keywords": ["리츠", "REITs", "부동산투자", "간접투자"],
        "category": "배당주",
    },
    {
        "id": "div-08",
        "topic": "배당주 포트폴리오 만들기: 업종 분산의 중요성",
        "keywords": ["배당포트폴리오", "분산투자", "업종분산", "자산배분"],
        "category": "배당주",
    },
    {
        "id": "div-09",
        "topic": "배당 재투자의 복리 효과: 20년 시뮬레이션",
        "keywords": ["배당재투자", "복리효과", "장기투자", "DRIP"],
        "category": "배당주",
    },
    {
        "id": "div-10",
        "topic": "은퇴 후 배당 수입으로 생활하기: 필요 자금 계산",
        "keywords": ["은퇴투자", "배당생활", "노후자금", "은퇴계획"],
        "category": "배당주",
    },
    # === 절세 (10) ===
    {
        "id": "tax-01",
        "topic": "연말정산 소득공제 완벽 가이드 (직장인 필독)",
        "keywords": ["연말정산", "소득공제", "세액공제", "직장인절세"],
        "category": "절세",
    },
    {
        "id": "tax-02",
        "topic": "ISA 계좌 200% 활용법: 비과세 혜택 총정리",
        "keywords": ["ISA", "ISA계좌", "비과세", "절세계좌"],
        "category": "절세",
    },
    {
        "id": "tax-03",
        "topic": "개인연금저축 vs IRP: 세액공제 최대로 받는 법",
        "keywords": ["연금저축", "IRP", "세액공제", "연금계좌"],
        "category": "절세",
    },
    {
        "id": "tax-04",
        "topic": "해외주식 양도소득세 절세 전략 5가지",
        "keywords": ["양도소득세", "해외주식세금", "절세전략", "세금신고"],
        "category": "절세",
    },
    {
        "id": "tax-05",
        "topic": "금융투자소득세 정리: 투자자가 알아야 할 모든 것",
        "keywords": ["금투세", "금융투자소득세", "주식세금", "세금개편"],
        "category": "절세",
    },
    {
        "id": "tax-06",
        "topic": "부동산 취득세·양도세 절세 핵심 포인트",
        "keywords": ["취득세", "양도세", "부동산세금", "절세팁"],
        "category": "절세",
    },
    {
        "id": "tax-07",
        "topic": "증여세 면제한도와 합법적 절세 방법",
        "keywords": ["증여세", "면제한도", "가족증여", "자산이전"],
        "category": "절세",
    },
    {
        "id": "tax-08",
        "topic": "프리랜서·사업자를 위한 종합소득세 절세 가이드",
        "keywords": ["종합소득세", "사업자절세", "프리랜서세금", "경비처리"],
        "category": "절세",
    },
    {
        "id": "tax-09",
        "topic": "연금 수령 시 세금 줄이는 전략적 인출 방법",
        "keywords": ["연금세금", "연금인출", "퇴직연금", "연금소득세"],
        "category": "절세",
    },
    {
        "id": "tax-10",
        "topic": "절세 계좌 총정리: ISA, 연금저축, IRP 비교",
        "keywords": ["절세계좌", "ISA비교", "연금비교", "계좌선택"],
        "category": "절세",
    },
    # === 부동산 (10) ===
    {
        "id": "re-01",
        "topic": "부동산 투자 초보자 가이드: 아파트 vs 오피스텔 vs 상가",
        "keywords": ["부동산투자", "아파트투자", "오피스텔", "상가투자"],
        "category": "부동산",
    },
    {
        "id": "re-02",
        "topic": "전세 vs 월세 vs 매매: 2025년 최적의 선택은?",
        "keywords": ["전세월세", "매매vs전세", "주거비교", "부동산선택"],
        "category": "부동산",
    },
    {
        "id": "re-03",
        "topic": "갭투자란? 장점과 위험성 완전 분석",
        "keywords": ["갭투자", "레버리지투자", "전세레버리지", "부동산위험"],
        "category": "부동산",
    },
    {
        "id": "re-04",
        "topic": "청약 가점제 완벽 분석: 당첨 확률 높이는 법",
        "keywords": ["청약", "가점제", "청약당첨", "아파트청약"],
        "category": "부동산",
    },
    {
        "id": "re-05",
        "topic": "수익형 부동산: 월세 수익률 계산하는 방법",
        "keywords": ["수익형부동산", "월세수익률", "임대수익", "투자수익"],
        "category": "부동산",
    },
    {
        "id": "re-06",
        "topic": "재건축·재개발 투자: 기회와 리스크 분석",
        "keywords": ["재건축", "재개발", "정비사업", "부동산기회"],
        "category": "부동산",
    },
    {
        "id": "re-07",
        "topic": "부동산 경매 입문: 권리분석부터 낙찰까지",
        "keywords": ["부동산경매", "경매입문", "권리분석", "낙찰"],
        "category": "부동산",
    },
    {
        "id": "re-08",
        "topic": "1인 가구를 위한 소형 부동산 투자 전략",
        "keywords": ["소형부동산", "1인가구", "원룸투자", "소액부동산"],
        "category": "부동산",
    },
    {
        "id": "re-09",
        "topic": "부동산 대출 총정리: LTV, DTI, DSR 이해하기",
        "keywords": ["부동산대출", "LTV", "DTI", "DSR"],
        "category": "부동산",
    },
    {
        "id": "re-10",
        "topic": "해외 부동산 투자: 동남아 vs 미국 vs 일본 비교",
        "keywords": ["해외부동산", "동남아투자", "미국부동산", "일본부동산"],
        "category": "부동산",
    },
    # === 재테크 기초 (10) ===
    {
        "id": "basic-01",
        "topic": "사회초년생 재테크 로드맵: 월급 200만원으로 시작하기",
        "keywords": ["사회초년생", "재테크시작", "월급관리", "첫투자"],
        "category": "재테크 기초",
    },
    {
        "id": "basic-02",
        "topic": "비상금 만들기: 적정 비상금 규모와 관리 방법",
        "keywords": ["비상금", "예비자금", "CMA", "파킹통장"],
        "category": "재테크 기초",
    },
    {
        "id": "basic-03",
        "topic": "72의 법칙으로 알아보는 복리의 마법",
        "keywords": ["72법칙", "복리", "복리계산", "투자수익"],
        "category": "재테크 기초",
    },
    {
        "id": "basic-04",
        "topic": "가계부 쓰는 법: 지출 관리의 시작",
        "keywords": ["가계부", "지출관리", "예산관리", "절약"],
        "category": "재테크 기초",
    },
    {
        "id": "basic-05",
        "topic": "적금 vs 예금 vs CMA: 여유자금 어디에 넣을까?",
        "keywords": ["적금", "예금", "CMA", "금리비교"],
        "category": "재테크 기초",
    },
    {
        "id": "basic-06",
        "topic": "투자 위험 관리: 분산투자와 자산배분의 기본",
        "keywords": ["분산투자", "자산배분", "리스크관리", "포트폴리오"],
        "category": "재테크 기초",
    },
    {
        "id": "basic-07",
        "topic": "경제 뉴스 읽는 법: 금리, 환율, 물가 이해하기",
        "keywords": ["경제뉴스", "금리", "환율", "물가"],
        "category": "재테크 기초",
    },
    {
        "id": "basic-08",
        "topic": "신용점수 올리는 실전 방법 7가지",
        "keywords": ["신용점수", "신용등급", "신용관리", "대출금리"],
        "category": "재테크 기초",
    },
    {
        "id": "basic-09",
        "topic": "20대·30대 자산 포트폴리오 설계 가이드",
        "keywords": ["자산배분", "포트폴리오", "20대투자", "30대투자"],
        "category": "재테크 기초",
    },
    {
        "id": "basic-10",
        "topic": "재테크 실패를 막는 흔한 실수 10가지",
        "keywords": ["투자실수", "재테크실패", "투자주의", "초보실수"],
        "category": "재테크 기초",
    },
]


class TopicManager:
    """토픽 큐 관리자 (다국어 지원)"""

    def __init__(self, lang: str = "ko"):
        self.lang = lang
        # 언어별 토픽 파일: topics_ko.json, topics_en.json, ...
        self.topics_file = DATA_DIR / f"topics_{lang}.json"
        self.history_file = DATA_DIR / f"published_history_{lang}.json"
        self.failed_file = DATA_DIR / f"failed_topics_{lang}.json"
        self._ensure_files()

    def _ensure_files(self):
        """파일이 없으면 초기 토픽으로 생성"""
        if not self.topics_file.exists():
            # ko는 DEFAULT_TOPICS, 다른 언어는 외부 JSON 파일 우선
            bundled = DATA_DIR / f"topics_{self.lang}_default.json"
            if bundled.exists():
                import shutil

                shutil.copy(bundled, self.topics_file)
            else:
                defaults = DEFAULT_TOPICS if self.lang == "ko" else []
                self._save_topics(defaults)
            logger.info(f"[{self.lang}] 초기 토픽 파일 생성 완료")

        if not self.history_file.exists():
            self._save_history([])

        if not self.failed_file.exists():
            self._save_failed([])

    def _load_topics(self) -> list[dict]:
        with open(self.topics_file, "r", encoding="utf-8") as f:
            return json.load(f)

    def _save_topics(self, topics: list[dict]):
        with open(self.topics_file, "w", encoding="utf-8") as f:
            json.dump(topics, f, ensure_ascii=False, indent=2)

    def _load_history(self) -> list[dict]:
        with open(self.history_file, "r", encoding="utf-8") as f:
            return json.load(f)

    def _save_history(self, history: list[dict]):
        with open(self.history_file, "w", encoding="utf-8") as f:
            json.dump(history, f, ensure_ascii=False, indent=2)

    def _load_failed(self) -> list[dict]:
        if not self.failed_file.exists():
            return []
        with open(self.failed_file) as f:
            return json.load(f)

    def _save_failed(self, items: list[dict]):
        with open(self.failed_file, "w", encoding="utf-8") as f:
            json.dump(items, f, ensure_ascii=False, indent=2)

    def mark_failed(self, topic_id: str, reason: str):
        """발행 실패 기록 — 다음날 재시도 큐에 추가"""
        failed = self._load_failed()
        existing = next((f for f in failed if f["topic_id"] == topic_id), None)
        if existing:
            existing["attempts"] += 1
            existing["last_failed_at"] = datetime.now().isoformat()
            existing["last_reason"] = reason
        else:
            failed.append(
                {
                    "topic_id": topic_id,
                    "attempts": 1,
                    "first_failed_at": datetime.now().isoformat(),
                    "last_failed_at": datetime.now().isoformat(),
                    "last_reason": reason,
                }
            )
        self._save_failed(failed)
        logger.info(f"실패 큐 등록: {topic_id} ({reason[:80]})")

    def clear_failed(self, topic_id: str):
        """재시도 성공 시 실패 큐에서 제거"""
        failed = [f for f in self._load_failed() if f["topic_id"] != topic_id]
        self._save_failed(failed)

    @staticmethod
    def _keyword_similarity(kw_a: list[str], title_a: str, kw_b: list[str], title_b: str) -> float:
        """두 토픽의 키워드+제목 기반 단어 집합 유사도 (Jaccard)"""
        def to_words(keywords: list[str], title: str) -> set[str]:
            words: set[str] = set()
            for kw in keywords:
                words.update(kw.lower().split())
            words.update(title.lower().split())
            return words

        words_a = to_words(kw_a, title_a)
        words_b = to_words(kw_b, title_b)
        if not words_a or not words_b:
            return 0.0
        intersection = words_a & words_b
        union = words_a | words_b
        return len(intersection) / len(union)

    def _get_recent_published_topics(self, days: int = 30) -> list[dict]:
        """최근 N일 이내 발행된 토픽 목록 반환 (키워드+제목 포함)"""
        try:
            history = self._load_history()
            topics = self._load_topics()
            topics_by_id = {t["id"]: t for t in topics}
            cutoff = datetime.now().timestamp() - days * 86400
            recent = []
            for h in history:
                try:
                    pub_ts = datetime.fromisoformat(h["published_at"]).timestamp()
                except (KeyError, ValueError):
                    continue
                if pub_ts >= cutoff:
                    topic = topics_by_id.get(h["topic_id"])
                    if topic:
                        recent.append(topic)
            return recent
        except Exception:
            return []

    def _is_duplicate_topic(self, candidate: dict, recent_topics: list[dict], threshold: float = 0.6) -> str | None:
        """
        후보 토픽이 최근 발행된 토픽과 중복인지 검사.
        중복이면 매칭된 토픽의 제목 반환, 아니면 None.
        """
        c_kw = candidate.get("keywords", [])
        c_title = candidate.get("topic", "")
        for recent in recent_topics:
            r_kw = recent.get("keywords", [])
            r_title = recent.get("topic", "")
            # 완전 일치 체크
            if c_title == r_title:
                return r_title
            # 유사도 체크
            sim = self._keyword_similarity(c_kw, c_title, r_kw, r_title)
            if sim >= threshold:
                return r_title
        return None

    def get_next_topic(self, topic_type: str = "blog") -> dict | None:
        """
        다음 발행할 토픽 반환 — 실패 재시도 우선, 그 다음 정상 큐

        Args:
            topic_type: "blog" (테이버형) 또는 "analysis_topic" (김단테형) 필터

        Returns:
            {"id", "topic", "keywords", "category"} or None
        """
        # 0) 시즌 캘린더 이벤트 우선 (D-3 이내)
        calendar = EventCalendar()
        event = calendar.get_upcoming_event()
        if event:
            return {
                "id": f"event-{event['name']}",
                "topic": event["topic"],
                "keywords": event["keywords"],
                "category": "시즌 이벤트",
            }

        topics = self._load_topics()
        history = self._load_history()
        failed = self._load_failed()
        published_ids = {h["topic_id"] for h in history}
        recent_topics = self._get_recent_published_topics(days=30)

        # 1) 실패 재시도 우선 (attempts < 3, 발행 안 됨)
        topics_by_id = {t["id"]: t for t in topics}
        for f in failed:
            if f["attempts"] >= 3:
                continue
            if f["topic_id"] in published_ids:
                continue
            candidate = topics_by_id.get(f["topic_id"])
            if candidate and candidate.get("type", "blog") == topic_type:
                matched = self._is_duplicate_topic(candidate, recent_topics)
                if matched:
                    logger.info(f"Skipping duplicate topic: {candidate['topic']} (similar to recent: {matched})")
                    continue
                logger.info(
                    f"실패 재시도: [{candidate['category']}] {candidate['topic']}"
                )
                return candidate

        # 2) 정상 큐
        for topic in topics:
            if topic["id"] in published_ids:
                continue
            # type 필드 없는 레거시 토픽은 blog로 취급
            if topic.get("type", "blog") != topic_type:
                continue
            matched = self._is_duplicate_topic(topic, recent_topics)
            if matched:
                logger.info(f"Skipping duplicate topic: {topic['topic']} (similar to recent: {matched})")
                continue
            logger.info(f"다음 토픽: [{topic['category']}] {topic['topic']}")
            return topic

        logger.warning(
            f"발행 가능한 {topic_type} 토픽이 없습니다. 새 토픽을 추가해주세요."
        )
        return None

    def mark_published(self, topic_id: str, platform: str, url: str):
        """토픽 발행 완료 기록"""
        history = self._load_history()
        history.append(
            {
                "topic_id": topic_id,
                "platform": platform,
                "url": url,
                "published_at": datetime.now().isoformat(),
            }
        )
        self._save_history(history)
        logger.info(f"발행 기록 완료: {topic_id} -> {platform} ({url})")

    def add_topic(self, topic: str, keywords: list[str], category: str) -> str:
        """새 토픽 추가"""
        topics = self._load_topics()
        topic_id = f"custom-{uuid.uuid4().hex[:8]}"
        topics.append(
            {
                "id": topic_id,
                "topic": topic,
                "keywords": keywords,
                "category": category,
            }
        )
        self._save_topics(topics)
        logger.info(f"토픽 추가: {topic_id} - {topic}")
        return topic_id

    def get_status(self) -> dict:
        """토픽 큐 상태 조회"""
        topics = self._load_topics()
        history = self._load_history()
        published_ids = {h["topic_id"] for h in history}

        total = len(topics)
        published = len([t for t in topics if t["id"] in published_ids])
        remaining = total - published

        # 카테고리별 통계
        categories = {}
        for t in topics:
            cat = t["category"]
            if cat not in categories:
                categories[cat] = {"total": 0, "published": 0, "remaining": 0}
            categories[cat]["total"] += 1
            if t["id"] in published_ids:
                categories[cat]["published"] += 1
            else:
                categories[cat]["remaining"] += 1

        return {
            "total": total,
            "published": published,
            "remaining": remaining,
            "categories": categories,
        }

    def get_history(self) -> list[dict]:
        """발행 이력 조회"""
        return self._load_history()
