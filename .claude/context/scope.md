# Multi-provider LLM Abstraction

## Vision

Permettre à chaque étape du pipeline (analyse offre, analyse entreprise, lettre de motivation) d'utiliser un modèle différent — Claude ou non — configurable via `.env`. Un `LLMClient` Protocol découple les services du SDK Anthropic, avec deux implémentations : Anthropic (natif, prompt cache préservé) et OpenAI-compatible (couvre GPT, Mistral, Groq, etc.).

## Success criteria

- [x] `.env` contient `ANALYSIS_MODEL`, `COMPANY_MODEL`, `GENERATION_MODEL` avec fallback sur `DEFAULT_MODEL`
- [x] `.env` accepte des API keys par provider (`OPENAI_API_KEY`, `MISTRAL_API_KEY`)
- [x] `LLMClient` Protocol avec `complete()` et `complete_with_tools()` dans `app/llm/`
- [x] `AnthropicLLMClient` préserve le prompt cache (`cache_control: ephemeral`)
- [x] `OpenAILLMClient` fonctionne avec un modèle OpenAI (tool_use inclus)
- [x] Chaque service (OfferAnalyzer, CompanyAnalyzer, CoverLetterGenerator) reçoit son propre `LLMClient`
- [x] `log_usage()` reçoit le `model_id` réel et résout le pricing correctement
- [x] Les 88 tests existants passent toujours
- [x] Nouveaux tests pour `AnthropicLLMClient` et `OpenAILLMClient` (mock)
