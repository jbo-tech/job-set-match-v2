"""OpenAI-compatible LLM client.

Covers OpenAI, Mistral, Groq, DeepSeek, and any provider exposing an
OpenAI-compatible endpoint. Uses the openai SDK with configurable base_url.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from openai import AsyncOpenAI

from app.llm.protocol import LLMResponse, ToolCall, ToolDefinition, ToolResult, Usage

logger = logging.getLogger(__name__)


class OpenAILLMClient:
    """LLMClient implementation for OpenAI-compatible APIs.

    Handles tool_use via OpenAI function calling format. Tracks cache tokens
    from usage when the provider reports them (OpenAI, Google).
    """

    def __init__(
        self,
        api_key: str,
        model: str,
        base_url: str | None = None,
    ) -> None:
        kwargs: dict[str, Any] = {"api_key": api_key}
        if base_url:
            kwargs["base_url"] = base_url
        self._client = AsyncOpenAI(**kwargs)
        self._model = model

    @property
    def model_id(self) -> str:
        return self._model

    async def complete(
        self,
        *,
        messages: list[dict[str, Any]],
        system: str,
        system_blocks: list[dict[str, Any]] | None = None,
        max_tokens: int = 8192,
        temperature: float = 0.2,
    ) -> LLMResponse:
        oai_messages = _build_messages(messages, system, system_blocks)

        response = await self._client.chat.completions.create(
            model=self._model,
            max_tokens=max_tokens,
            temperature=temperature,
            messages=oai_messages,
        )
        return _to_llm_response(response)

    async def complete_with_tools(
        self,
        *,
        messages: list[dict[str, Any]],
        system: str,
        system_blocks: list[dict[str, Any]] | None = None,
        tools: list[ToolDefinition],
        max_tokens: int = 8192,
        temperature: float = 0.2,
    ) -> LLMResponse:
        oai_messages = _build_messages(messages, system, system_blocks)
        oai_tools = [
            {
                "type": "function",
                "function": {
                    "name": t.name,
                    "description": t.description,
                    "parameters": t.input_schema,
                },
            }
            for t in tools
        ]

        response = await self._client.chat.completions.create(
            model=self._model,
            max_tokens=max_tokens,
            temperature=temperature,
            messages=oai_messages,
            tools=oai_tools,
        )
        return _to_llm_response(response)

    def format_assistant_message(self, response: LLMResponse) -> dict[str, Any]:
        msg: dict[str, Any] = {"role": "assistant", "content": response.text or None}
        if response.tool_calls:
            msg["tool_calls"] = [
                {
                    "id": tc.id,
                    "type": "function",
                    "function": {
                        "name": tc.name,
                        "arguments": json.dumps(tc.arguments),
                    },
                }
                for tc in response.tool_calls
            ]
        return msg

    def format_tool_results(self, results: list[ToolResult]) -> list[dict[str, Any]]:
        return [
            {
                "role": "tool",
                "tool_call_id": r.tool_call_id,
                "content": r.content,
            }
            for r in results
        ]


def _build_messages(
    messages: list[dict[str, Any]],
    system: str,
    system_blocks: list[dict[str, Any]] | None,
) -> list[dict[str, Any]]:
    """Prepend system message. Flattens Anthropic system_blocks to text."""
    if system_blocks:
        parts = []
        for block in system_blocks:
            text = block.get("text", "")
            if text:
                parts.append(text)
        system_text = "\n\n".join(parts)
    else:
        system_text = system

    return [{"role": "system", "content": system_text}, *messages]


def _to_llm_response(response) -> LLMResponse:
    """Convert OpenAI ChatCompletion response to LLMResponse."""
    choice = response.choices[0] if response.choices else None
    if not choice:
        return LLMResponse(model=response.model or "")

    message = choice.message
    text = message.content or ""
    tool_calls = []

    if message.tool_calls:
        for tc in message.tool_calls:
            try:
                args = json.loads(tc.function.arguments)
            except (json.JSONDecodeError, TypeError):
                args = {}
            tool_calls.append(
                ToolCall(
                    id=tc.id,
                    name=tc.function.name,
                    arguments=args,
                )
            )

    usage_obj = response.usage
    cache_creation = 0
    cache_read = 0
    if usage_obj:
        # OpenAI reports cache tokens in prompt_tokens_details
        details = getattr(usage_obj, "prompt_tokens_details", None)
        if details:
            cache_read = getattr(details, "cached_tokens", 0) or 0

    usage = Usage(
        input_tokens=getattr(usage_obj, "prompt_tokens", 0) if usage_obj else 0,
        output_tokens=getattr(usage_obj, "completion_tokens", 0) if usage_obj else 0,
        cache_creation_tokens=cache_creation,
        cache_read_tokens=cache_read,
    )

    stop_reason = "tool_use" if tool_calls else "end_turn"

    return LLMResponse(
        text=text,
        tool_calls=tool_calls,
        usage=usage,
        model=response.model or "",
        stop_reason=stop_reason,
    )
