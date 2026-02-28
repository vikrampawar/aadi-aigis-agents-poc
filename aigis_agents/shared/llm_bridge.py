"""
LLM bridge — provides get_chat_model() for aigis-agents.

Priority order:
  1. Import get_chat_model from aigis-poc worker (if available in PYTHONPATH)
  2. Instantiate directly from LangChain using environment variables / session_keys
"""

from __future__ import annotations

import os
from typing import Any


def get_chat_model(model_key: str | None = None, session_keys: dict[str, str] | None = None) -> Any:
    """
    Return a LangChain chat model. Tries to reuse aigis-poc's model registry
    first; falls back to direct instantiation if not available.
    """
    # Attempt to reuse aigis-poc LLM registry
    try:
        import sys
        # Add worker directory to path if running from aigis-poc repo
        worker_paths = [
            os.path.join(os.path.dirname(__file__), "..", "..", "..", "worker"),
            os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", "worker"),
        ]
        for wp in worker_paths:
            if os.path.isdir(wp) and wp not in sys.path:
                sys.path.insert(0, wp)
        from src.llm import get_chat_model as _aigis_get_chat_model
        return _aigis_get_chat_model(model_key, session_keys)
    except ImportError:
        pass

    # Fallback: direct instantiation
    _model_key = model_key or "gpt-4o-mini"

    _OPENAI_COMPAT = {
        "gpt-4o-mini", "gpt-4.1-nano", "gpt-4.1-mini", "gpt-4.1", "gpt-4o",
        "o3-mini", "o4-mini", "o3",
        "deepseek", "deepseek-reasoner",
        "kimi-k2", "minimax", "qwen3-235b",
    }
    _ANTHROPIC = {"claude-opus", "claude-sonnet"}

    def _resolve_key(env_var: str) -> str | None:
        val = os.environ.get(env_var)
        if val:
            return val
        if session_keys:
            return session_keys.get(env_var)
        return None

    if _model_key in _ANTHROPIC:
        from langchain_anthropic import ChatAnthropic
        api_key = _resolve_key("ANTHROPIC_API_KEY")
        model_name = "claude-opus-4-5" if "opus" in _model_key else "claude-sonnet-4-5"
        return ChatAnthropic(model=model_name, api_key=api_key, temperature=0.1)

    # Default: OpenAI-compatible
    from langchain_openai import ChatOpenAI
    api_key = _resolve_key("OPENAI_API_KEY")
    model_name = _model_key  # use as-is for most models
    kwargs: dict[str, Any] = {"model": model_name, "api_key": api_key, "temperature": 0.1}

    # Reasoning models don't support temperature
    if _model_key in {"o3-mini", "o4-mini", "o3", "deepseek-reasoner"}:
        del kwargs["temperature"]

    # Non-OpenAI providers need base_url
    _BASE_URLS = {
        "deepseek": "https://api.deepseek.com/v1",
        "deepseek-reasoner": "https://api.deepseek.com/v1",
        "kimi-k2": "https://api.moonshot.ai/v1",
        "minimax": "https://api.minimax.io/v1",
        "qwen3-235b": "https://dashscope.aliyuncs.com/compatible-mode/v1",
    }
    if _model_key in _BASE_URLS:
        kwargs["base_url"] = _BASE_URLS[_model_key]

    return ChatOpenAI(**kwargs)


def estimate_cost(model_key: str, input_tokens: int, output_tokens: int) -> float:
    """Estimate USD cost. Falls back to gpt-4o-mini pricing if model unknown."""
    try:
        import sys
        worker_paths = [
            os.path.join(os.path.dirname(__file__), "..", "..", "..", "worker"),
            os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", "worker"),
        ]
        for wp in worker_paths:
            if os.path.isdir(wp) and wp not in sys.path:
                sys.path.insert(0, wp)
        from src.llm import estimate_cost as _aigis_cost
        return _aigis_cost(model_key, input_tokens, output_tokens)
    except ImportError:
        pass

    # Fallback pricing ($/MTok)
    _PRICING = {
        "gpt-4o-mini": (0.15, 0.60),
        "gpt-4.1": (2.00, 8.00),
        "gpt-4o": (2.50, 10.00),
        "claude-sonnet": (3.00, 15.00),
        "claude-opus": (15.00, 75.00),
    }
    cost_in, cost_out = _PRICING.get(model_key, (0.15, 0.60))
    return (input_tokens / 1_000_000) * cost_in + (output_tokens / 1_000_000) * cost_out
