"""LLMClient protocol and shared response types.

Defines the provider-agnostic interface that all LLM clients implement.
Two methods: complete() for single-shot calls, complete_with_tools() for
agentic tool-use loops.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol, runtime_checkable


@dataclass(frozen=True)
class ToolCall:
    """A tool invocation requested by the model."""

    id: str
    name: str
    arguments: dict[str, Any]


@dataclass(frozen=True)
class Usage:
    """Token usage for a single API call."""

    input_tokens: int = 0
    output_tokens: int = 0
    cache_creation_tokens: int = 0
    cache_read_tokens: int = 0


@dataclass(frozen=True)
class LLMResponse:
    """Provider-agnostic response from an LLM call."""

    text: str = ""
    tool_calls: list[ToolCall] = field(default_factory=list)
    usage: Usage = field(default_factory=Usage)
    model: str = ""
    stop_reason: str = ""


@dataclass(frozen=True)
class ToolDefinition:
    """Provider-agnostic tool definition."""

    name: str
    description: str
    input_schema: dict[str, Any]


@dataclass(frozen=True)
class ToolResult:
    """Result of a tool execution, to be sent back to the model."""

    tool_call_id: str
    content: str
    is_error: bool = False


@runtime_checkable
class LLMClient(Protocol):
    """Provider-agnostic LLM client interface."""

    @property
    def model_id(self) -> str:
        """The model identifier used by this client."""
        ...

    async def complete(
        self,
        *,
        messages: list[dict[str, Any]],
        system: str,
        system_blocks: list[dict[str, Any]] | None = None,
        max_tokens: int = 8192,
        temperature: float = 0.2,
    ) -> LLMResponse:
        """Single-shot completion.

        Args:
            messages: Conversation messages in provider-native format.
            system: System instruction as plain text.
            system_blocks: Optional Anthropic-style system blocks with
                          cache_control. Anthropic clients use these when
                          provided; other clients flatten to system text.
            max_tokens: Maximum tokens to generate.
            temperature: Sampling temperature.
        """
        ...

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
        """Completion with tool definitions.

        Returns an LLMResponse whose stop_reason is "tool_use" if the model
        wants to call a tool, with tool_calls populated. Otherwise stop_reason
        is "end_turn" and text contains the final answer.
        """
        ...

    def format_assistant_message(self, response: LLMResponse) -> dict[str, Any]:
        """Format an LLMResponse as an assistant message for conversation history.

        Each provider has its own format for representing tool_use in the
        conversation history. This method builds the correct message dict.
        """
        ...

    def format_tool_results(self, results: list[ToolResult]) -> list[dict[str, Any]]:
        """Format tool execution results as message(s) for conversation history.

        Anthropic wraps all results in a single user message with
        tool_result content blocks. OpenAI uses individual tool-role messages.
        """
        ...
