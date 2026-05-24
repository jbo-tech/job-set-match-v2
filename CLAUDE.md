# Job Set & Match V2

## Stack
- Python 3.11+, FastAPI, multi-provider LLM (Anthropic SDK + OpenAI SDK)
- Appels Python directs : httpx + bs4 (fetch), Playwright (PDF), httpx REST (Brave Search)
- Plugin Firefox Manifest V3
- Output : vault Obsidian (fichiers Markdown + frontmatter)

## Commands
```bash
uv run uvicorn app.main:app --reload        # dev server (port 8000)
uv run pytest                                # tests (140 tests)
uv run python -m app.main <URL> [fichier] [--refresh] [--temperature 0.5]  # mode CLI
uv run playwright install chromium           # setup Playwright (une fois)
```

## Endpoints
- `GET /health` — sante (sans auth)
- `GET /stats` — statistiques tokens/couts session (avec auth)
- `POST /analyze` — analyse d'offre (avec auth)

## Securite
- Auth : header `X-Auth-Token` verifie via `hmac.compare_digest`
- SSRF : `_validate_url()` dans content_fetcher bloque IPs privees, schemes non-HTTP, DNS resolution
- Path traversal : `ensure_within()` dans paths.py
- CORS : restreint aux extensions Firefox (`moz-extension://`)

## Conventions
- Commentaires et docstrings : français
- Noms de variables/fonctions : anglais
- Commits : anglais, conventional commits
- Config via `.env` (voir `.env.example`)

## Structure
```
app/               # backend FastAPI + logique metier
  config.py        # Pydantic Settings (.env)
  main.py          # FastAPI app + endpoint /analyze + mode CLI
  models.py        # schemas Pydantic (request/response/analysis)
  pipeline.py      # orchestrateur central
  vault_layout.py  # parse vault_layout.yaml (Pydantic)
  llm/             # abstraction multi-provider (protocol, anthropic_client,
                   # openai_client, factory)
  middleware/       # auth token
  prompts/         # prompts LLM (analysis, company, generation, outreach)
  services/        # offer_analyzer, company_analyzer, cover_letter, outreach_generator,
                   # content_fetcher, document_loader, obsidian_writer, brave_search,
                   # prompt_loader
  utils/           # dedup, paths (safe_slug + vault_slug), token_logger, pricing
plugin/            # extension Firefox (manifest.json, extract.js, popup, service_worker)
tests/             # pytest + pytest-asyncio
_prompts_archive/  # prompts V1 (reference)
vault_layout.yaml  # config structure vault Obsidian
```

## Pricing
Les couts tokens sont resolus dynamiquement via `pricing.json` (LiteLLM, partage avec `~/Wip/coding/mcp/llm-sparring/pricing.json`). Ne pas hardcoder de tarifs dans `config.py`.

## Context
Quand pertinent, lire :
- Travail en cours : `.claude/context/status.md`
- Erreurs passees : `.claude/context/anti-patterns.md`
- Decisions techniques : `.claude/context/decisions.md`
- Plan detaille : `V2_PLAN.md`
- Spec vault : `APP_INTEGRATION_SPEC.md`

## Fin de session
Lancer `/retro` avant d'arreter pour mettre a jour les fichiers de contexte.
