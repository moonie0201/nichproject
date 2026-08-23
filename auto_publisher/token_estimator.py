"""
Token estimation and cost calculation for LLM CLI subprocess calls.

Provides word-count based token estimation for Claude and Gemini models,
since CLI subprocess output doesn't include token counts.
"""

import logging
import re

logger = logging.getLogger(__name__)

# Model pricing (per million tokens: input / output)
MODEL_PRICING = {
    "claude-haiku-4-5": {"input": 0.80, "output": 4.00},
    "claude-sonnet-4-6": {"input": 3.00, "output": 15.00},
    "claude-opus-4-7": {"input": 15.00, "output": 75.00},
    "gemini-3.1-pro-preview": {"input": 5.00, "output": 15.00},
    "gemini-3-flash-preview": {"input": 0.30, "output": 2.50},
    "gemini-2.5-pro": {"input": 5.00, "output": 15.00},
    "gemini-2.5-flash": {"input": 0.30, "output": 2.50},
}


def estimate_tokens(text: str) -> int:
    """
    Estimate token count using word-count approximation.

    Heuristic:
    - English: 1 word ≈ 1.3 tokens
    - Korean/CJK (U+AC00~U+D7A3): 1 char ≈ 1.5 tokens

    Args:
        text: Input text (English or Korean/CJK mixed)

    Returns:
        Estimated token count
    """
    if not text:
        return 0

    # Count Korean characters (가-힣 range: U+AC00 to U+D7A3)
    korean_chars = len(re.findall(r"[가-힣]", text))

    # Count English words (sequences of alphanumeric + hyphens, apostrophes)
    english_words = len(re.findall(r"\b[a-zA-Z0-9\-']+\b", text))

    # Count other CJK characters (Chinese, Japanese)
    other_cjk = len(re.findall(r"[一-鿿぀-ゟ゠-ヿ]", text))

    # Token estimation
    korean_tokens = int(korean_chars * 1.5)
    english_tokens = int(english_words * 1.3)
    other_cjk_tokens = int(other_cjk * 1.5)

    total = korean_tokens + english_tokens + other_cjk_tokens

    # Minimum 1 token for non-empty text
    return max(1, total)


def estimate_cost(model: str, input_tokens: int, output_tokens: int) -> float:
    """
    Calculate cost in USD for LLM call.

    Args:
        model: Model name (e.g., "claude-haiku-4-5", "gemini-2.5-flash")
        input_tokens: Estimated input token count
        output_tokens: Estimated output token count

    Returns:
        Cost in USD. Returns 0.0 for unknown models.
    """
    if model not in MODEL_PRICING:
        logger.warning(f"Unknown model: {model}. Returning cost 0.0")
        return 0.0

    pricing = MODEL_PRICING[model]

    # Convert to millions for pricing calculation
    input_cost = (input_tokens / 1_000_000) * pricing["input"]
    output_cost = (output_tokens / 1_000_000) * pricing["output"]

    return round(input_cost + output_cost, 6)


def estimate_call(prompt: str, response: str, model: str) -> dict:
    """
    Estimate tokens and cost for a single LLM call.

    Args:
        prompt: Input prompt text
        response: LLM response text
        model: Model name

    Returns:
        Dict with keys:
        - input_tokens: Estimated prompt tokens
        - output_tokens: Estimated response tokens
        - cost_usd: Total cost in USD
        - provider: 'anthropic' or 'google' (or other based on model)
    """
    input_tokens = estimate_tokens(prompt)
    output_tokens = estimate_tokens(response)
    cost_usd = estimate_cost(model, input_tokens, output_tokens)

    # Determine provider from model name
    if model.startswith("claude-"):
        provider = "anthropic"
    elif model.startswith("gemini-"):
        provider = "google"
    else:
        provider = "unknown"

    return {
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "cost_usd": cost_usd,
        "provider": provider,
    }
