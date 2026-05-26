"""Tests pour l'abstraction LLM multi-provider (protocol, clients, factory)."""

import json
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.llm.anthropic_client import AnthropicLLMClient, _to_llm_response
from app.llm.factory import create_llm_client
from app.llm.openai_client import OpenAILLMClient
from app.llm.openai_client import _to_llm_response as _oai_to_llm_response
from app.llm.protocol import (
    LLMClient,
    LLMResponse,
    ToolCall,
    ToolDefinition,
    ToolResult,
    Usage,
)


# ═══════════════════════════════════════════════════════════════ Protocol types

class TestProtocolTypes:
    def test_llm_response_defaults(self):
        r = LLMResponse()
        assert r.text == ""
        assert r.tool_calls == []
        assert r.model == ""
        assert r.stop_reason == ""
        assert r.usage == Usage()

    def test_tool_call(self):
        tc = ToolCall(id="tc_1", name="search", arguments={"query": "test"})
        assert tc.name == "search"
        assert tc.arguments["query"] == "test"

    def test_tool_definition(self):
        td = ToolDefinition(
            name="brave_search",
            description="Search the web",
            input_schema={"type": "object", "properties": {}},
        )
        assert td.name == "brave_search"

    def test_tool_result(self):
        tr = ToolResult(tool_call_id="tc_1", content="result text")
        assert not tr.is_error
        tr_err = ToolResult(tool_call_id="tc_2", content="oops", is_error=True)
        assert tr_err.is_error

    def test_usage(self):
        u = Usage(input_tokens=100, output_tokens=50, cache_read_tokens=30)
        assert u.input_tokens == 100
        assert u.cache_creation_tokens == 0


# ═══════════════════════════════════════════════════════════════ Anthropic Client

class TestAnthropicClient:
    def test_model_id(self):
        with patch("app.llm.anthropic_client.AsyncAnthropic"):
            client = AnthropicLLMClient(api_key="test", model="claude-sonnet-4-20250514")
        assert client.model_id == "claude-sonnet-4-20250514"

    def test_to_llm_response_text(self):
        raw = SimpleNamespace(
            content=[SimpleNamespace(type="text", text="Hello world")],
            usage=SimpleNamespace(
                input_tokens=10, output_tokens=20,
                cache_creation_input_tokens=5, cache_read_input_tokens=3,
            ),
            model="claude-sonnet-4-20250514",
            stop_reason="end_turn",
        )
        r = _to_llm_response(raw)
        assert r.text == "Hello world"
        assert r.tool_calls == []
        assert r.stop_reason == "end_turn"
        assert r.usage.input_tokens == 10
        assert r.usage.cache_creation_tokens == 5
        assert r.usage.cache_read_tokens == 3

    def test_to_llm_response_tool_use(self):
        raw = SimpleNamespace(
            content=[
                SimpleNamespace(type="text", text="Searching..."),
                SimpleNamespace(
                    type="tool_use", id="tc_1", name="brave_search",
                    input={"query": "Acme Corp"},
                ),
            ],
            usage=SimpleNamespace(
                input_tokens=10, output_tokens=20,
                cache_creation_input_tokens=0, cache_read_input_tokens=0,
            ),
            model="claude-sonnet-4-20250514",
            stop_reason="tool_use",
        )
        r = _to_llm_response(raw)
        assert r.text == "Searching..."
        assert len(r.tool_calls) == 1
        assert r.tool_calls[0].name == "brave_search"
        assert r.tool_calls[0].arguments == {"query": "Acme Corp"}
        assert r.stop_reason == "tool_use"

    async def test_complete_uses_system_blocks_when_provided(self):
        with patch("app.llm.anthropic_client.AsyncAnthropic") as mock_cls:
            mock_anthropic = MagicMock()
            mock_anthropic.messages.create = AsyncMock(return_value=SimpleNamespace(
                content=[SimpleNamespace(type="text", text="response")],
                usage=SimpleNamespace(
                    input_tokens=10, output_tokens=5,
                    cache_creation_input_tokens=0, cache_read_input_tokens=0,
                ),
                model="claude-test",
                stop_reason="end_turn",
            ))
            mock_cls.return_value = mock_anthropic

            client = AnthropicLLMClient(api_key="test", model="claude-test")
            blocks = [{"type": "text", "text": "sys", "cache_control": {"type": "ephemeral"}}]
            await client.complete(
                messages=[{"role": "user", "content": "hi"}],
                system="sys plain",
                system_blocks=blocks,
            )

            call_kwargs = mock_anthropic.messages.create.call_args.kwargs
            assert call_kwargs["system"] == blocks

    async def test_complete_uses_system_string_without_blocks(self):
        with patch("app.llm.anthropic_client.AsyncAnthropic") as mock_cls:
            mock_anthropic = MagicMock()
            mock_anthropic.messages.create = AsyncMock(return_value=SimpleNamespace(
                content=[SimpleNamespace(type="text", text="response")],
                usage=SimpleNamespace(
                    input_tokens=10, output_tokens=5,
                    cache_creation_input_tokens=0, cache_read_input_tokens=0,
                ),
                model="claude-test",
                stop_reason="end_turn",
            ))
            mock_cls.return_value = mock_anthropic

            client = AnthropicLLMClient(api_key="test", model="claude-test")
            await client.complete(
                messages=[{"role": "user", "content": "hi"}],
                system="sys plain",
            )

            call_kwargs = mock_anthropic.messages.create.call_args.kwargs
            assert call_kwargs["system"] == "sys plain"

    def test_format_assistant_message(self):
        with patch("app.llm.anthropic_client.AsyncAnthropic"):
            client = AnthropicLLMClient(api_key="test", model="claude-test")

        response = LLMResponse(
            text="thinking",
            tool_calls=[ToolCall(id="tc_1", name="search", arguments={"q": "test"})],
        )
        msg = client.format_assistant_message(response)
        assert msg["role"] == "assistant"
        assert len(msg["content"]) == 2
        assert msg["content"][0] == {"type": "text", "text": "thinking"}
        assert msg["content"][1]["type"] == "tool_use"
        assert msg["content"][1]["id"] == "tc_1"

    def test_format_tool_results(self):
        with patch("app.llm.anthropic_client.AsyncAnthropic"):
            client = AnthropicLLMClient(api_key="test", model="claude-test")

        results = [
            ToolResult(tool_call_id="tc_1", content="found it"),
            ToolResult(tool_call_id="tc_2", content="error", is_error=True),
        ]
        msgs = client.format_tool_results(results)
        assert len(msgs) == 1
        assert msgs[0]["role"] == "user"
        content = msgs[0]["content"]
        assert len(content) == 2
        assert content[0]["tool_use_id"] == "tc_1"
        assert "is_error" not in content[0]
        assert content[1]["is_error"] is True


# ═══════════════════════════════════════════════════════════════ OpenAI Client

class TestOpenAIClient:
    def test_model_id(self):
        with patch("app.llm.openai_client.AsyncOpenAI"):
            client = OpenAILLMClient(api_key="test", model="gpt-4o-mini")
        assert client.model_id == "gpt-4o-mini"

    def test_to_llm_response_text(self):
        raw = SimpleNamespace(
            choices=[SimpleNamespace(
                message=SimpleNamespace(content="Hello", tool_calls=None),
            )],
            usage=SimpleNamespace(
                prompt_tokens=10, completion_tokens=20,
                prompt_tokens_details=SimpleNamespace(cached_tokens=5),
            ),
            model="gpt-4o-mini",
        )
        r = _oai_to_llm_response(raw)
        assert r.text == "Hello"
        assert r.tool_calls == []
        assert r.stop_reason == "end_turn"
        assert r.usage.input_tokens == 10
        assert r.usage.output_tokens == 20
        assert r.usage.cache_read_tokens == 5

    def test_to_llm_response_tool_calls(self):
        raw = SimpleNamespace(
            choices=[SimpleNamespace(
                message=SimpleNamespace(
                    content="",
                    tool_calls=[
                        SimpleNamespace(
                            id="tc_1",
                            function=SimpleNamespace(
                                name="brave_search",
                                arguments='{"query": "Acme"}',
                            ),
                        )
                    ],
                ),
            )],
            usage=SimpleNamespace(
                prompt_tokens=10, completion_tokens=5,
                prompt_tokens_details=None,
            ),
            model="gpt-4o-mini",
        )
        r = _oai_to_llm_response(raw)
        assert len(r.tool_calls) == 1
        assert r.tool_calls[0].name == "brave_search"
        assert r.tool_calls[0].arguments == {"query": "Acme"}
        assert r.stop_reason == "tool_use"

    def test_to_llm_response_no_usage(self):
        raw = SimpleNamespace(
            choices=[SimpleNamespace(
                message=SimpleNamespace(content="Hi", tool_calls=None),
            )],
            usage=None,
            model="gpt-4o-mini",
        )
        r = _oai_to_llm_response(raw)
        assert r.usage.input_tokens == 0

    def test_format_assistant_message(self):
        with patch("app.llm.openai_client.AsyncOpenAI"):
            client = OpenAILLMClient(api_key="test", model="gpt-4o-mini")

        response = LLMResponse(
            text="",
            tool_calls=[ToolCall(id="tc_1", name="search", arguments={"q": "test"})],
        )
        msg = client.format_assistant_message(response)
        assert msg["role"] == "assistant"
        assert msg["content"] is None  # empty string → None for OpenAI
        assert len(msg["tool_calls"]) == 1
        assert msg["tool_calls"][0]["type"] == "function"
        assert json.loads(msg["tool_calls"][0]["function"]["arguments"]) == {"q": "test"}

    def test_format_tool_results(self):
        with patch("app.llm.openai_client.AsyncOpenAI"):
            client = OpenAILLMClient(api_key="test", model="gpt-4o-mini")

        results = [
            ToolResult(tool_call_id="tc_1", content="found it"),
            ToolResult(tool_call_id="tc_2", content="error", is_error=True),
        ]
        msgs = client.format_tool_results(results)
        assert len(msgs) == 2
        assert all(m["role"] == "tool" for m in msgs)
        assert msgs[0]["tool_call_id"] == "tc_1"
        assert msgs[1]["tool_call_id"] == "tc_2"

    async def test_complete_prepends_system_message(self):
        with patch("app.llm.openai_client.AsyncOpenAI") as mock_cls:
            mock_openai = MagicMock()
            mock_openai.chat.completions.create = AsyncMock(return_value=SimpleNamespace(
                choices=[SimpleNamespace(
                    message=SimpleNamespace(content="ok", tool_calls=None),
                )],
                usage=SimpleNamespace(
                    prompt_tokens=10, completion_tokens=5,
                    prompt_tokens_details=None,
                ),
                model="gpt-4o-mini",
            ))
            mock_cls.return_value = mock_openai

            client = OpenAILLMClient(api_key="test", model="gpt-4o-mini")
            await client.complete(
                messages=[{"role": "user", "content": "hi"}],
                system="you are helpful",
            )

            call_kwargs = mock_openai.chat.completions.create.call_args.kwargs
            msgs = call_kwargs["messages"]
            assert msgs[0]["role"] == "system"
            assert msgs[0]["content"] == "you are helpful"
            assert msgs[1]["role"] == "user"

    async def test_complete_flattens_system_blocks(self):
        with patch("app.llm.openai_client.AsyncOpenAI") as mock_cls:
            mock_openai = MagicMock()
            mock_openai.chat.completions.create = AsyncMock(return_value=SimpleNamespace(
                choices=[SimpleNamespace(
                    message=SimpleNamespace(content="ok", tool_calls=None),
                )],
                usage=SimpleNamespace(
                    prompt_tokens=10, completion_tokens=5,
                    prompt_tokens_details=None,
                ),
                model="gpt-4o-mini",
            ))
            mock_cls.return_value = mock_openai

            client = OpenAILLMClient(api_key="test", model="gpt-4o-mini")
            blocks = [
                {"type": "text", "text": "instruction"},
                {"type": "text", "text": "<docs>content</docs>", "cache_control": {"type": "ephemeral"}},
            ]
            await client.complete(
                messages=[{"role": "user", "content": "hi"}],
                system="unused",
                system_blocks=blocks,
            )

            call_kwargs = mock_openai.chat.completions.create.call_args.kwargs
            system_content = call_kwargs["messages"][0]["content"]
            assert "instruction" in system_content
            assert "<docs>content</docs>" in system_content


# ═══════════════════════════════════════════════════════════════ Factory

class TestFactory:
    def test_anthropic_model(self):
        with patch("app.llm.factory.AnthropicLLMClient") as mock:
            create_llm_client("claude-sonnet-4-20250514", {"anthropic": "key"})
            mock.assert_called_once_with(api_key="key", model="claude-sonnet-4-20250514")

    def test_openai_model(self):
        with patch("app.llm.factory.OpenAILLMClient") as mock:
            create_llm_client("gpt-4o-mini", {"openai": "key"})
            mock.assert_called_once_with(api_key="key", model="gpt-4o-mini", base_url=None)

    def test_mistral_model(self):
        with patch("app.llm.factory.OpenAILLMClient") as mock:
            create_llm_client("mistral-large-latest", {"mistral": "key"})
            mock.assert_called_once_with(
                api_key="key", model="mistral-large-latest",
                base_url="https://api.mistral.ai/v1",
            )

    def test_groq_strips_prefix(self):
        with patch("app.llm.factory.OpenAILLMClient") as mock:
            create_llm_client("groq/llama-3.1-70b", {"groq": "key"})
            mock.assert_called_once_with(
                api_key="key", model="llama-3.1-70b",
                base_url="https://api.groq.com/openai/v1",
            )

    def test_deepseek_model(self):
        with patch("app.llm.factory.OpenAILLMClient") as mock:
            create_llm_client("deepseek-chat", {"deepseek": "key"})
            mock.assert_called_once_with(
                api_key="key", model="deepseek-chat",
                base_url="https://api.deepseek.com",
            )

    def test_google_model(self):
        with patch("app.llm.factory.OpenAILLMClient") as mock:
            create_llm_client("gemini-2.5-flash", {"google": "key"})
            mock.assert_called_once_with(
                api_key="key", model="gemini-2.5-flash",
                base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
            )

    def test_missing_api_key_raises(self):
        with pytest.raises(ValueError, match="Pas d'API key"):
            create_llm_client("gpt-4o", {"anthropic": "key"})

    def test_unknown_model_raises(self):
        with pytest.raises(ValueError, match="Provider inconnu"):
            create_llm_client("llama-local", {"anthropic": "key"})


# ═══════════════════════════════════════════════════════════════ Config helpers

class TestConfigHelpers:
    def test_resolve_model_fallback(self):
        from app.config import LLMModelsConfig
        m = LLMModelsConfig()
        assert m.resolve("analysis") == "claude-sonnet-4-20250514"
        assert m.resolve("company") == "claude-sonnet-4-20250514"
        assert m.resolve("generation") == "claude-sonnet-4-20250514"

    def test_resolve_model_override(self):
        from app.config import LLMModelsConfig
        m = LLMModelsConfig(analysis="claude-haiku-3-20250414")
        assert m.resolve("analysis") == "claude-haiku-3-20250414"
        assert m.resolve("company") == "claude-sonnet-4-20250514"

    def test_api_keys_property(self):
        from app.config import Settings
        s = Settings(
            anthropic_api_key="anth-key",
            auth_token="tok",
            openai_api_key="oai-key",
            mistral_api_key="",
        )
        keys = s.api_keys
        assert keys["anthropic"] == "anth-key"
        assert keys["openai"] == "oai-key"
        assert "mistral" not in keys
