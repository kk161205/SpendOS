"""
Groq LLM client wrapper.
Provides a thin abstraction over langchain-groq with retry handling.
"""

import asyncio
import logging
from typing import Optional
from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage, SystemMessage
from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


def get_groq_llm(model_name: str, temperature: float = 0.1) -> ChatGroq:
    """
    Instantiate a ChatGroq LLM for the given model.
    
    Args:
        model_name: One of the Groq model identifiers.
        temperature: Sampling temperature (0.0 = deterministic).
    
    Returns:
        Configured ChatGroq instance.
    """
    return ChatGroq(
        model=model_name,
        temperature=temperature,
        max_tokens=settings.llm_max_tokens,
        groq_api_key=settings.groq_api_key,
    )


async def invoke_llm(
    model_name: str,
    system_prompt: str,
    user_prompt: str,
    temperature: float = 0.1,
) -> str:
    """
    Invoke a Groq LLM and return the text response.
    
    Args:
        model_name: Groq model identifier.
        system_prompt: System message to set LLM context.
        user_prompt: The actual task prompt.
        temperature: Sampling temperature.
    
    Returns:
        LLM text response string.
    """
    llm = get_groq_llm(model_name, temperature)
    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_prompt),
    ]
    try:
        # Add a delay before the request to prevent hitting rate limits
        await asyncio.sleep(2.5)
        response = await llm.ainvoke(messages)
        return response.content
    except Exception as e:
        logger.error(f"Groq LLM error (model={model_name}): {e}")
        raise
