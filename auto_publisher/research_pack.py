"""Source-grounded research pack for automated video generation.

This module intentionally avoids browser automation or unofficial NotebookLM
APIs. n8n can call the existing /make-video flow and get NotebookLM-like,
source-grounded structure from local blog/chart inputs.
"""

from __future__ import annotations

import re


_NUMBER_RE = re.compile(r"(?:\$?\d[\d,]*\.?\d*%?|[0-9]+년|[0-9]+개월|[0-9]+배)")


def _trim(text: str, limit: int = 120) -> str:
    cleaned = re.sub(r"\s+", " ", text or "").strip(" ,.")
    if len(cleaned) <= limit:
        return cleaned
    return cleaned[: limit - 1].rstrip() + "…"


def _numbers(text: str, limit: int = 3) -> list[str]:
    seen: list[str] = []
    for match in _NUMBER_RE.findall(text or ""):
        if match not in seen:
            seen.append(match)
        if len(seen) >= limit:
            break
    return seen


def _scene_type(idx: int, sentence: str) -> str:
    text = sentence or ""
    if idx == 0:
        return "thesis_board"
    if any(token in text for token in ("리스크", "위험", "변동성", "금리", "다만", "반면")):
        return "risk_matrix"
    if len(_numbers(text)) >= 2:
        return "market_dashboard"
    return "timeline"


def build_research_pack(
    *,
    title: str,
    headings: list[str],
    key_points: list[str],
    risk_points: list[str],
    source_data_points: list[dict],
    chart_paths: list[str],
    blog_url: str = "",
) -> dict:
    """Build a NotebookLM-like source pack from already available sources."""
    claims = []
    for idx, point in enumerate(source_data_points[:5]):
        evidence = point.get("anchor_sentence") or point.get("context") or ""
        claims.append(
            {
                "claim": _trim(evidence or point.get("label") or title, 110),
                "evidence": _trim(evidence, 140),
                "numbers": _numbers(point.get("value", "") + " " + evidence, 3),
                "confidence": point.get("confidence", "inferred"),
                "source": blog_url or "local_blog",
                "priority": point.get("priority", "body"),
                "visual_scene": _scene_type(idx, evidence),
            }
        )

    counterpoints = [_trim(line, 130) for line in risk_points[:3]]
    if not counterpoints:
        counterpoints = [
            _trim(point.get("context", ""), 130)
            for point in source_data_points
            if point.get("priority") == "risk"
        ][:2]

    visual_scenes = []
    scene_sources = key_points[:4] or [point.get("context", "") for point in source_data_points[:4]]
    for idx, sentence in enumerate(scene_sources):
        visual_scenes.append(
            {
                "scene_type": _scene_type(idx, sentence),
                "headline": _trim(headings[min(idx, len(headings) - 1)] if headings else title, 42),
                "supporting_text": _trim(sentence, 92),
                "numbers": _numbers(sentence, 3),
                "chart": chart_paths[min(idx, len(chart_paths) - 1)] if chart_paths else None,
            }
        )

    return {
        "research_style": "source_grounded_notebook",
        "core_thesis": _trim(key_points[0] if key_points else title, 130),
        "claims": claims,
        "counterpoints": [line for line in counterpoints if line],
        "visual_scenes": visual_scenes,
        "source_count": 1 + len(chart_paths),
        "source_types": ["blog_markdown"] + (["chart_png"] if chart_paths else []),
    }
