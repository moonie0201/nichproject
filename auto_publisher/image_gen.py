"""로컬 이미지 생성 — 3 모델 백엔드 A/B 테스트 지원.

Backends:
  - flux_schnell (Apache 2.0, 12B, 4-step, 2x GPU split for fp16)
  - qwen_image (Apache 2.0, 20B, Multi-GPU, CN/CJK text 강점)
  - z_image_turbo (Apache 2.0, 6B, 8-step, single GPU fit)

Env:
  IMAGE_GEN_ENABLED=0/1  (기본 OFF — opt-in)
  IMAGE_GEN_MODEL=flux_schnell|qwen_image|z_image_turbo  (기본 z_image_turbo)
  HF_HOME=/home/mh/ocstorage/hf_cache  (모델 weights 위치)

Output:
  web/static/images/{slug}/cover-ai.png

설계:
  - Lazy import (torch/diffusers/...) — pytest는 mock으로 통과
  - 단일 함수 entry: generate_cover_image(slug, title, primary_keyword, lang)
  - 캐시: 기존 cover-ai.png 있으면 재사용
  - GPU OOM 시 자동 cpu_offload 폴백
"""
from __future__ import annotations

import logging
import os
import re
from pathlib import Path

logger = logging.getLogger(__name__)

WEB_STATIC_IMAGES = Path("/home/mh/ocstorage/workspace/nichproject/web/static/images")
DEFAULT_MODEL = "z_image_turbo"
SUPPORTED_BACKENDS = ("flux_schnell", "qwen_image", "z_image_turbo", "hidream_o1")


def _enabled() -> bool:
    return os.getenv("IMAGE_GEN_ENABLED", "0").strip() == "1"


def _selected_backend() -> str:
    backend = os.getenv("IMAGE_GEN_MODEL", DEFAULT_MODEL).strip().lower()
    if backend not in SUPPORTED_BACKENDS:
        logger.warning(f"unknown IMAGE_GEN_MODEL '{backend}', falling back to {DEFAULT_MODEL}")
        return DEFAULT_MODEL
    return backend


def _build_prompt(title: str, primary_keyword: str, lang: str) -> str:
    """투자 블로그 cover 이미지 prompt.

    노트: diffusion 모델은 "no text" 같은 부정문을 종종 무시 (negation 약함).
    text 관련 단어 자체를 prompt에서 제거 + 시각 요소만 묘사하는 게 더 효과적.
    """
    kw = (primary_keyword or "").strip().lower()

    # 키워드 기반 시각 테마
    theme_hint = "financial market"
    if any(t in kw for t in ("voo", "spy", "qqq", "sp500", "s&p500", "nasdaq")):
        theme_hint = "rising stock market chart with green candles"
    elif any(t in kw for t in ("schd", "배당", "dividend", "jepi", "jepq")):
        theme_hint = "golden coins stacked with growth arrows"
    elif any(t in kw for t in ("etf", "운용보수", "expense")):
        theme_hint = "modern fintech dashboard with charts"
    elif any(t in kw for t in ("배당", "은퇴", "irp", "isa", "연금")):
        theme_hint = "warm sunset over modern city skyline financial district"

    return (
        f"Photorealistic finance illustration, {theme_hint}, "
        f"clean minimalist composition, blue and gold color palette, "
        f"soft bokeh background, sharp focus, depth of field, "
        f"editorial photography style, 8k uhd, professional, high quality, "
        f"no letters, no numbers, no logo, no watermark"
    )


# ─────────────────────────────────────────────────────────────────────────────
# Backend: Z-Image-Turbo (default — 6B, RTX 3060 single fit)
# ─────────────────────────────────────────────────────────────────────────────
def _gen_z_image_turbo(prompt: str, out_path: Path, width: int = 1024, height: int = 1024) -> None:
    import torch
    from diffusers import ZImagePipeline

    pipe = ZImagePipeline.from_pretrained(
        "Tongyi-MAI/Z-Image-Turbo",
        torch_dtype=torch.bfloat16,
        low_cpu_mem_usage=True,
    )
    # RTX 3060 12GB는 6B bf16에 빠듯 — sequential offload로 layer-by-layer
    pipe.enable_sequential_cpu_offload()
    image = pipe(
        prompt=prompt,
        height=height,
        width=width,
        num_inference_steps=8,
        guidance_scale=0.0,
    ).images[0]
    image.save(out_path)


# ─────────────────────────────────────────────────────────────────────────────
# Backend: FLUX.1-schnell (12B, 2 GPU split for fp16 quality)
# ─────────────────────────────────────────────────────────────────────────────
def _gen_flux_schnell(prompt: str, out_path: Path, width: int = 1024, height: int = 1024) -> None:
    import torch
    from diffusers import FluxPipeline

    # 2 GPU split: device_map="balanced" 가 layer-level split 수행
    pipe = FluxPipeline.from_pretrained(
        "black-forest-labs/FLUX.1-schnell",
        torch_dtype=torch.bfloat16,
    )
    if torch.cuda.device_count() >= 2:
        try:
            pipe.enable_model_cpu_offload()  # 2 GPU split fallback
        except Exception:
            pipe.to("cuda:0")
    else:
        pipe.enable_model_cpu_offload()

    image = pipe(
        prompt=prompt,
        guidance_scale=0.0,
        num_inference_steps=4,
        max_sequence_length=256,
        height=height,
        width=width,
    ).images[0]
    image.save(out_path)


# ─────────────────────────────────────────────────────────────────────────────
# Backend: Qwen-Image (20B, Multi-GPU API, CJK text 강점)
# ─────────────────────────────────────────────────────────────────────────────
def _gen_qwen_image(prompt: str, out_path: Path, width: int = 1024, height: int = 1024) -> None:
    import torch
    from diffusers import QwenImagePipeline

    pipe = QwenImagePipeline.from_pretrained(
        "Qwen/Qwen-Image",
        torch_dtype=torch.bfloat16,
        low_cpu_mem_usage=True,
    )
    # 20B는 RTX 3060 12GB 단일에 unloaded — sequential layer offload 필수
    pipe.enable_sequential_cpu_offload()

    image = pipe(
        prompt=prompt,
        height=height,
        width=width,
        num_inference_steps=30,
        guidance_scale=4.0,
    ).images[0]
    image.save(out_path)


def _gen_hidream_o1(prompt: str, out_path: Path, width: int = 1024, height: int = 1024) -> None:
    """HiDream-O1-Image (8B, MIT, SOTA May 2026) via subprocess inference.py.

    ⚠️ RTX 3090/4090/A100 (24GB+ 단일 GPU) 환경에서만 동작.
    RTX 3060 12GB 단일에선 OOM (8B bf16 = 16GB), 4-bit 양자화는 silu CUDA op 비호환,
    multi-GPU split은 모델 코드가 자체 device 관리로 비호환.

    Repo: /home/mh/ocstorage/HiDream-O1-Image
    HF cache: /home/mh/ocstorage/hf_cache/hub/models--HiDream-ai--HiDream-O1-Image/snapshots/*/
    """
    import subprocess
    from glob import glob

    repo = Path("/home/mh/ocstorage/HiDream-O1-Image")
    if not repo.exists():
        raise RuntimeError(f"HiDream-O1 repo not cloned: {repo}")

    # Resolve snapshot path
    snaps = glob("/home/mh/ocstorage/hf_cache/hub/models--HiDream-ai--HiDream-O1-Image/snapshots/*/")
    if not snaps:
        raise RuntimeError("HiDream-O1 weights not downloaded")
    model_path = sorted(snaps)[-1].rstrip("/")

    # HiDream-O1은 transformers==4.57.1 고정 — 메인 venv (5.8.1)와 충돌하므로 전용 venv 사용
    hidream_python = "/home/mh/ocstorage/venv_hidream/bin/python3"
    if not Path(hidream_python).exists():
        raise RuntimeError(
            f"hidream venv 미설치: {hidream_python}. "
            "python3 -m venv /home/mh/ocstorage/venv_hidream && "
            "pip install -r HiDream-O1-Image/requirements.txt"
        )
    cmd = [
        hidream_python, str(repo / "inference.py"),
        "--model_path", model_path,
        "--prompt", prompt,
        "--output_image", str(out_path),
        "--height", str(height),
        "--width", str(width),
        "--model_type", "dev",  # faster (28 steps vs 50)
        "--guidance_scale", "0.0",  # dev mode default
        "--shift", "1.0",
    ]
    env = os.environ.copy()
    env["PYTHONPATH"] = str(repo) + ":" + env.get("PYTHONPATH", "")
    env["HF_HOME"] = "/home/mh/ocstorage/hf_cache"
    env["PYTORCH_CUDA_ALLOC_CONF"] = "expandable_segments:True"

    r = subprocess.run(cmd, env=env, cwd="/home/mh/ocstorage/workspace/nichproject",
                       capture_output=True, text=True, timeout=1200)
    if r.returncode != 0:
        raise RuntimeError(f"HiDream-O1 inference failed: {r.stderr[-500:]}")


_BACKENDS = {
    "z_image_turbo": _gen_z_image_turbo,
    "flux_schnell": _gen_flux_schnell,
    "qwen_image": _gen_qwen_image,
    "hidream_o1": _gen_hidream_o1,
}


def generate_cover_image(
    slug: str,
    title: str,
    primary_keyword: str = "",
    lang: str = "ko",
    backend: str | None = None,
    force_regen: bool = False,
) -> str | None:
    """Cover image 생성. 성공 시 절대 경로 (str), 실패/비활성 시 None.

    Args:
        slug: 포스트 slug (출력 경로 결정)
        title: 포스트 제목
        primary_keyword: SEO primary kw
        lang: 언어 (현재 prompt는 영문 기반)
        backend: 명시 백엔드 override (None이면 env IMAGE_GEN_MODEL)
        force_regen: True면 기존 cover-ai.png 무시하고 재생성
    """
    if not _enabled():
        return None

    backend = backend or _selected_backend()
    if backend not in _BACKENDS:
        logger.error(f"unsupported backend: {backend}")
        return None

    # 슬러그 정리 (파일시스템 안전)
    safe_slug = re.sub(r"[^\w\-가-힣]", "-", slug)[:80].strip("-")
    out_dir = WEB_STATIC_IMAGES / safe_slug
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "cover-ai.png"

    if out_path.exists() and not force_regen:
        logger.info(f"cover-ai 캐시 존재: {out_path}")
        return str(out_path)

    prompt = _build_prompt(title, primary_keyword, lang)
    logger.info(f"image_gen 시작: backend={backend} slug={safe_slug}")

    try:
        _BACKENDS[backend](prompt, out_path)
    except Exception as e:
        logger.error(f"image_gen 실패 (backend={backend}): {e}", exc_info=True)
        return None

    if out_path.exists() and out_path.stat().st_size > 1024:
        logger.info(f"image_gen 완료: {out_path} ({out_path.stat().st_size//1024}KB)")
        return str(out_path)
    return None


def ab_test(prompt: str, output_dir: str = "/tmp/ab_test") -> dict[str, str]:
    """3 백엔드 동일 prompt로 동시 생성 → 비교용 (수동 평가)."""
    if not _enabled():
        logger.error("IMAGE_GEN_ENABLED=0; A/B test 비활성")
        return {}

    od = Path(output_dir)
    od.mkdir(parents=True, exist_ok=True)
    results: dict[str, str] = {}
    for backend in SUPPORTED_BACKENDS:
        out = od / f"{backend}.png"
        logger.info(f"[A/B] {backend} 생성 중...")
        try:
            _BACKENDS[backend](prompt, out)
            results[backend] = str(out) if out.exists() else "FAIL"
        except Exception as e:
            logger.error(f"[A/B] {backend} 실패: {e}")
            results[backend] = f"ERROR: {e}"
    return results
