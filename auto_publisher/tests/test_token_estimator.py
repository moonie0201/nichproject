import pytest
from auto_publisher.token_estimator import (
    estimate_tokens,
    estimate_cost,
    estimate_call,
)


class TestEstimateTokens:
    """Test word-count based token estimation."""

    def test_english_only(self):
        """English text: 1 word ≈ 1.3 tokens"""
        text = "hello world"  # 2 words
        tokens = estimate_tokens(text)
        # 2 * 1.3 = 2.6 → int(2.6) = 2
        assert tokens == 2

    def test_korean_only(self):
        """Korean text: 1 char ≈ 1.5 tokens"""
        text = "한글"  # 2 Korean chars
        tokens = estimate_tokens(text)
        # 2 * 1.5 = 3.0 → int(3.0) = 3
        assert tokens == 3

    def test_mixed_english_korean(self):
        """Mixed English and Korean text"""
        text = "Hello 한글 World"  # 2 English words + 2 Korean chars
        tokens = estimate_tokens(text)
        # English: 2 * 1.3 = 2.6 → 2
        # Korean: 2 * 1.5 = 3.0 → 3
        # Total: 5
        assert tokens == 5

    def test_empty_string(self):
        """Empty string returns 0"""
        assert estimate_tokens("") == 0

    def test_whitespace_only(self):
        """Whitespace-only string returns minimum 1"""
        assert estimate_tokens("   ") == 1

    def test_long_english_text(self):
        """Longer English text estimation"""
        text = "The quick brown fox jumps over the lazy dog"  # 9 words
        tokens = estimate_tokens(text)
        # 9 * 1.3 = 11.7 → 11
        assert tokens == 11

    def test_long_korean_text(self):
        """Longer Korean text estimation"""
        text = "이것은 한글 테스트 문장입니다"  # 13 Korean chars
        tokens = estimate_tokens(text)
        # 13 * 1.5 = 19.5 → 19
        assert tokens == 19


class TestEstimateCost:
    """Test cost calculation for different models."""

    def test_claude_haiku(self):
        """Claude Haiku pricing: $0.80 / $4 per Mtok"""
        # 1000 input tokens, 1000 output tokens
        cost = estimate_cost("claude-haiku-4-5", 1000, 1000)
        # (1000 / 1M * 0.80) + (1000 / 1M * 4.00) = 0.00080 + 0.00400 = 0.00480
        assert abs(cost - 0.00480) < 0.000001

    def test_claude_sonnet(self):
        """Claude Sonnet pricing: $3 / $15 per Mtok"""
        cost = estimate_cost("claude-sonnet-4-6", 1000, 1000)
        # (1000 / 1M * 3) + (1000 / 1M * 15) = 0.003 + 0.015 = 0.018
        assert abs(cost - 0.018) < 0.000001

    def test_claude_opus(self):
        """Claude Opus pricing: $15 / $75 per Mtok"""
        cost = estimate_cost("claude-opus-4-7", 1000, 1000)
        # (1000 / 1M * 15) + (1000 / 1M * 75) = 0.015 + 0.075 = 0.090
        assert abs(cost - 0.090) < 0.000001

    def test_gemini_3_1_pro(self):
        """Gemini 3.1 Pro pricing: $5 / $15 per Mtok"""
        cost = estimate_cost("gemini-3.1-pro-preview", 1000, 1000)
        # (1000 / 1M * 5) + (1000 / 1M * 15) = 0.005 + 0.015 = 0.020
        assert abs(cost - 0.020) < 0.000001

    def test_gemini_3_flash(self):
        """Gemini 3 Flash pricing: $0.30 / $2.50 per Mtok"""
        cost = estimate_cost("gemini-3-flash-preview", 1000, 1000)
        # (1000 / 1M * 0.30) + (1000 / 1M * 2.50) = 0.0003 + 0.0025 = 0.0028
        assert abs(cost - 0.0028) < 0.000001

    def test_gemini_2_5_pro(self):
        """Gemini 2.5 Pro pricing: $5 / $15 per Mtok"""
        cost = estimate_cost("gemini-2.5-pro", 1000, 1000)
        # (1000 / 1M * 5) + (1000 / 1M * 15) = 0.005 + 0.015 = 0.020
        assert abs(cost - 0.020) < 0.000001

    def test_gemini_2_5_flash(self):
        """Gemini 2.5 Flash pricing: $0.30 / $2.50 per Mtok"""
        cost = estimate_cost("gemini-2.5-flash", 1000, 1000)
        # (1000 / 1M * 0.30) + (1000 / 1M * 2.50) = 0.0003 + 0.0025 = 0.0028
        assert abs(cost - 0.0028) < 0.000001

    def test_unknown_model(self):
        """Unknown model returns 0.0"""
        cost = estimate_cost("unknown-model-xyz", 1000, 1000)
        assert cost == 0.0

    def test_zero_tokens(self):
        """Zero tokens returns 0.0 cost"""
        cost = estimate_cost("claude-haiku-4-5", 0, 0)
        assert cost == 0.0

    def test_large_token_counts(self):
        """Large token counts calculated correctly"""
        # 1M tokens input, 1M tokens output
        cost = estimate_cost("claude-haiku-4-5", 1_000_000, 1_000_000)
        # (1M / 1M * 0.80) + (1M / 1M * 4.00) = 0.80 + 4.00 = 4.80
        assert abs(cost - 4.80) < 0.000001


class TestEstimateCall:
    """Test complete LLM call estimation."""

    def test_anthropic_provider_routing(self):
        """Claude models routed to 'anthropic' provider"""
        result = estimate_call("Hello", "World", "claude-haiku-4-5")
        assert result["provider"] == "anthropic"
        assert result["input_tokens"] > 0
        assert result["output_tokens"] > 0
        assert result["cost_usd"] >= 0

    def test_google_provider_routing(self):
        """Gemini models routed to 'google' provider"""
        result = estimate_call("Hello", "World", "gemini-2.5-flash")
        assert result["provider"] == "google"
        assert result["input_tokens"] > 0
        assert result["output_tokens"] > 0
        assert result["cost_usd"] >= 0

    def test_estimate_call_haiku(self):
        """Haiku model cost estimation in estimate_call"""
        prompt = "Hello world"  # ~2 tokens
        response = "Hi there"  # ~2 tokens
        result = estimate_call(prompt, response, "claude-haiku-4-5")

        assert result["input_tokens"] == 2
        assert result["output_tokens"] == 2
        assert result["provider"] == "anthropic"
        # (2 / 1M * 0.80) + (2 / 1M * 4.00) ≈ 0.0000096
        assert result["cost_usd"] > 0

    def test_estimate_call_korean(self):
        """Korean text in estimate_call"""
        prompt = "안녕"  # 2 chars * 1.5 = 3 tokens
        response = "반갑습니다"  # 5 chars * 1.5 = 7.5 → 7 tokens
        result = estimate_call(prompt, response, "gemini-2.5-flash")

        assert result["input_tokens"] == 3
        assert result["output_tokens"] == 7
        assert result["provider"] == "google"
        assert result["cost_usd"] >= 0

    def test_estimate_call_mixed_content(self):
        """Mixed English and Korean content"""
        prompt = "Translate to Korean: Hello world"  # "Translate to Korean Hello world" = 4 words * 1.3 ≈ 5 tokens
        response = "안녕하세요 세계"  # 6 chars * 1.5 = 9 tokens
        result = estimate_call(prompt, response, "gemini-3-flash-preview")

        assert result["provider"] == "google"
        assert result["input_tokens"] > 0
        assert result["output_tokens"] > 0
        assert result["cost_usd"] >= 0

    def test_estimate_call_returns_dict_structure(self):
        """Returns dict with required keys"""
        result = estimate_call("prompt", "response", "claude-sonnet-4-6")

        required_keys = {"input_tokens", "output_tokens", "cost_usd", "provider"}
        assert set(result.keys()) == required_keys
        assert isinstance(result["input_tokens"], int)
        assert isinstance(result["output_tokens"], int)
        assert isinstance(result["cost_usd"], float)
        assert isinstance(result["provider"], str)

    def test_estimate_call_unknown_model(self):
        """Unknown model in estimate_call returns 0 cost"""
        result = estimate_call("prompt", "response", "unknown-model")
        assert result["provider"] == "unknown"
        assert result["cost_usd"] == 0.0
