"""Anthropic LLM client — wraps AsyncAnthropic with prompt cache support."""

from __future__ import annotations

import logging
from typing import Any

from anthropic import AsyncAnthropic

from app.llm.protocol import LLMResponse, ToolCall, ToolDefinition, ToolResult, Usage

logger = logging.getLogger(__name__)


class AnthropicLLMClient:
    """LLMClient implementation for Anthropic models.

    Preserves native features: cache_control ephemeral on system blocks,
    native tool_use format, and cache token tracking.
    """

    def __init__(self, api_key: str, model: str) -> None:
        self._client = AsyncAnthropic(api_key=api_key)
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
        system_param = system_blocks if system_blocks else system

        response = await self._client.messages.create(
            model=self._model,
            max_tokens=max_tokens,
            temperature=temperature,
            system=system_param,
            messages=messages,
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
        system_param = system_blocks if system_blocks else system
        anthropic_tools = [
            {
                "name": t.name,
                "description": t.description,
                "input_schema": t.input_schema,
            }
            for t in tools
        ]

        response = await self._client.messages.create(
            model=self._model,
            max_tokens=max_tokens,
            temperature=temperature,
            system=system_param,
            tools=anthropic_tools,
            messages=messages,
        )
        return _to_llm_response(response)

    def format_assistant_message(self, response: LLMResponse) -> dict[str, Any]:
        blocks: list[dict[str, Any]] = []
        if response.text:
            blocks.append({"type": "text", "text": response.text})
        for tc in response.tool_calls:
            blocks.append({
                "type": "tool_use",
                "id": tc.id,
                "name": tc.name,
                "input": tc.arguments,
            })
        return {"role": "assistant", "content": blocks}

    def format_tool_results(self, results: list[ToolResult]) -> list[dict[str, Any]]:
        content = []
        for r in results:
            block: dict[str, Any] = {
                "type": "tool_result",
                "tool_use_id": r.tool_call_id,
                "content": r.content,
            }
            if r.is_error:
                block["is_error"] = True
            content.append(block)
        return [{"role": "user", "content": content}]


def _to_llm_response(response) -> LLMResponse:
    """Convert Anthropic API response to LLMResponse."""
    text_parts = []
    tool_calls = []

    for block in response.content:
        block_type = getattr(block, "type", None)
        if block_type == "text":
            text_parts.append(block.text)
        elif block_type == "tool_use":
            tool_calls.append(
                ToolCall(
                    id=block.id,
                    name=block.name,
                    arguments=block.input,
                )
            )

    usage_obj = response.usage
    usage = Usage(
        input_tokens=getattr(usage_obj, "input_tokens", 0),
        output_tokens=getattr(usage_obj, "output_tokens", 0),
        cache_creation_tokens=getattr(usage_obj, "cache_creation_input_tokens", 0) or 0,
        cache_read_tokens=getattr(usage_obj, "cache_read_input_tokens", 0) or 0,
    )

    stop_reason = "tool_use" if response.stop_reason == "tool_use" else "end_turn"

    return LLMResponse(
        text="\n".join(text_parts).strip(),
        tool_calls=tool_calls,
        usage=usage,
        model=response.model,
        stop_reason=stop_reason,
    )
