"""
Groq LLM client wrapper.
Provides a thin abstraction over langchain-groq with retry handling.
"""

import asyncio
import logging
import re
from typing import Optional
from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage, SystemMessage
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception,
    before_sleep_log,
)
from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


def is_transient_error(exception):
    """Check if exception is a 429 Rate Limit or 5xx Server Error."""
    err_str = str(exception).lower()
    transient_indicators = ["429", "rate limit", "500", "502", "503", "504", "server error", "timeout"]
    return any(indicator in err_str for indicator in transient_indicators)


def wait_retry_after_or_exponential():
    """Custom wait strategy that respects Retry-After hints or falls back to exponential backoff."""
    exp_wait = wait_exponential(multiplier=1, min=2, max=10)
    
    def _wait(retry_state):
        exc = retry_state.outcome.exception()
        if exc:
            # Extract retry delay from common LLM error messages if present
            # e.g., "Rate limit reached. Please try again in 5.2s."
            match = re.search(r"try again in ([\d.]+)s", str(exc))
            if match:
                return float(match.group(1))
        return exp_wait(retry_state=retry_state)
    return _wait


def get_groq_llm(model_name: str, temperature: float = 0.1) -> ChatGroq:
    """
    Instantiate a ChatGroq LLM for the given model.
    """
    return ChatGroq(
        model=model_name,
        temperature=temperature,
        max_tokens=settings.llm_max_tokens,
        groq_api_key=settings.groq_api_key,
    )


@retry(
    stop=stop_after_attempt(5),
    wait=wait_retry_after_or_exponential(),
    retry=retry_if_exception(is_transient_error),
    before_sleep=before_sleep_log(logger, logging.WARNING),
    reraise=True,
)
async def invoke_llm(
    model_name: str,
    system_prompt: str,
    user_prompt: str,
    temperature: float = 0.1,
) -> str:
    """
    Invoke a Groq LLM and return the text response with automatic retries.
    """
    llm = get_groq_llm(model_name, temperature)
    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_prompt),
    ]
    response = await llm.ainvoke(messages)
    return response.content
