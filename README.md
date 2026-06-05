# Job Set & Match V2

Outil personnel de veille emploi : capture d'offre depuis Firefox, analyse Claude (offre + entreprise + profil), dossier structure ecrit dans un vault Obsidian, dashboard via Obsidian Bases.

## Stack

- **Backend** : Python 3.11+, FastAPI, multi-provider LLM (Anthropic SDK + OpenAI SDK)
- **Fetch** : httpx + BeautifulSoup (texte), Playwright (PDF)
- **Recherche** : Brave Search API
- **Plugin** : Firefox Manifest V3
- **Output** : vault Obsidian (Markdown + frontmatter YAML)

## Setup

```bash
# Python 3.11+ requis (pyenv recommande)
pyenv local 3.12.3

# Dependances
uv sync --extra dev

# Playwright (capture PDF)
uv run playwright install chromium

# Configuration
cp .env.example .env
# Renseigner : ANTHROPIC_API_KEY, AUTH_TOKEN, OBSIDIAN_VAULT_PATH
# Optionnel : BRAVE_API_KEY (+ clés providers). Config métier → config.yaml
```

## Usage

### Serveur (pour le plugin Firefox)

```bash
uv run uvicorn app.main:app --reload
```

### CLI

```bash
# Depuis un fichier
uv run python -m app.main https://example.com/offre chemin/offre.txt

# Depuis stdin
cat offre.txt | uv run python -m app.main https://example.com/offre

# Forcer la re-analyse (bypass caches)
uv run python -m app.main https://example.com/offre offre.txt --refresh

# Override temperature pour la lettre de motivation
uv run python -m app.main https://example.com/offre offre.txt --temperature 0.5
```

### Plugin Firefox

1. Ouvrir `about:debugging#/runtime/this-firefox`
2. "Charger un module temporaire" → selectionner `plugin/manifest.json`
3. Cliquer l'icone → Parametres → renseigner l'URL backend et le token
4. Naviguer sur une offre d'emploi → cliquer "Analyser cette offre"

### Tests

```bash
uv run python -m pytest
```

## Configuration

Les **secrets** vivent dans `.env` ; toute la **config métier** (vault, modèles, seuils) vit dans `config.yaml`.

### `.env` — secrets

| Variable | Description | Defaut |
|----------|-------------|--------|
| `ANTHROPIC_API_KEY` | Cle API Anthropic | *requis* |
| `AUTH_TOKEN` | Token d'authentification pour le plugin | *requis* |
| `BRAVE_API_KEY` | Cle API Brave Search (analyse entreprise) | *(vide = desactive)* |
| `OPENAI_API_KEY` | Cle API OpenAI (si un modele gpt-* est configure) | *(vide)* |
| `MISTRAL_API_KEY` | Cle API Mistral | *(vide)* |
| `DEEPSEEK_API_KEY` | Cle API DeepSeek | *(vide)* |
| `GROQ_API_KEY` | Cle API Groq | *(vide)* |
| `GOOGLE_API_KEY` | Cle API Google (Gemini) | *(vide)* |

### `config.yaml` — config metier

| Section | Cle | Description | Defaut |
|---------|-----|-------------|--------|
| `vault` | `vault_root` | Chemin absolu vers le vault Obsidian | *requis* |
| `vault` | `paths` | Chemins relatifs (applications, companies, archive) | voir fichier |
| `vault` | `personal_docs` | Docs perso injectes dans les prompts | voir fichier |
| `llm.models` | `default` | Modele par defaut | `claude-sonnet-4-20250514` |
| `llm.models` | `analysis` | Override modele analyse offre | `""` (fallback) |
| `llm.models` | `company` | Override modele analyse entreprise | `""` (fallback) |
| `llm.models` | `generation` | Override modele generation lettre | `""` (fallback) |
| `llm.models` | `outreach` | Override modele outreach | `""` (fallback) |
| `llm` | `temperatures` | Temperature par tache : `analysis` (scoring, ~0.2), `generation` (lettre, ~0.7), `outreach` (~0.5) | `0.2 / 0.7 / 0.5` |
| `llm` | `max_tokens` | Tokens max par reponse LLM | `8192` |
| `llm` | `max_tokens_outreach` | Tokens max pour l'outreach (sorties courtes) | `4096` |
| `server` | `score_threshold` | Seuil `chanceRating` (1-10) pour generer la lettre. `0.0` = toujours | `0.0` |
| `server` | `host` / `port` | Bind serveur | `127.0.0.1:8000` |

#### Modeles multi-provider

Le provider est determine par le **prefixe** du `model_id`. Ajouter la cle API correspondante dans `.env`.

| Prefixe | Provider | Cle API `.env` | Exemples |
|---------|----------|----------------|----------|
| `claude-*` | Anthropic | `ANTHROPIC_API_KEY` | `claude-sonnet-4-20250514`, `claude-haiku-4-20250514` |
| `gpt-*`, `o1-*`, `o3-*`, `o4-*`, `chatgpt-*` | OpenAI | `OPENAI_API_KEY` | `gpt-4o`, `gpt-4o-mini`, `o4-mini` |
| `mistral*` | Mistral | `MISTRAL_API_KEY` | `mistral-large-latest`, `mistral-small-latest` |
| `deepseek*` | DeepSeek | `DEEPSEEK_API_KEY` | `deepseek-chat`, `deepseek-reasoner` |
| `groq/*` | Groq | `GROQ_API_KEY` | `groq/llama-3.1-70b-versatile` |
| `gemini*` | Google | `GOOGLE_API_KEY` | `gemini-2.5-flash`, `gemini-2.5-pro` |

Exemple — utiliser GPT-4o par defaut, Mistral pour la lettre, et Claude pour l'analyse :
```yaml
llm:
  models:
    default: gpt-4o-mini
    analysis: claude-sonnet-4-20250514
    generation: mistral-large-latest
```

## Structure du projet

```
app/                          # Backend FastAPI + logique metier
  config.py                   # Pydantic Settings — charge .env (secrets) et config.yaml (métier)
  main.py                     # Point d'entree FastAPI (/analyze, /health) + mode CLI
  models.py                   # Schemas Pydantic — contrats partages (request, response, analyse)
  pipeline.py                 # Orchestrateur central — enchaine les etapes d'analyse
  vault_layout.py             # Parse section vault de config.yaml — structure du vault Obsidian

  middleware/
    auth.py                   # Middleware auth — verifie X-Auth-Token sur chaque requete

  prompts/
    __init__.py               # Re-exporte les constantes de prompts
    analysis.py               # ANALYSIS_PROMPT — grille d'evaluation offre/profil (JSON)
    company.py                # COMPANY_PROMPT — template rapport entreprise (Markdown)
    context.py                # CONTEXT_PROMPT — (reserve, non utilise dans le MVP)
    generation.py             # GENERATION_PROMPT — template lettre de motivation
    outreach.py               # OUTREACH_PROMPT — accroche LinkedIn, email intro, suggestions CV

  services/
    brave_search.py           # Client Brave Search API — recherche web pour CompanyAnalyzer
    company_analyzer.py       # Analyse entreprise via LLM + Brave Search (boucle tool_use)
    content_fetcher.py        # Fetch texte (httpx+bs4) et capture PDF (Playwright)
    cover_letter.py           # Generation lettre de motivation via LLM
    document_loader.py        # Charge les docs perso depuis le vault (CV, pitch, etc.)
    obsidian_writer.py        # Ecrit les artefacts dans le vault (offre, analyse, lettre, PDF)
    offer_analyzer.py         # Analyse offre via LLM (ANALYSIS_PROMPT + docs perso)
    outreach_generator.py     # Generation accroche LinkedIn, email intro, suggestions CV
    prompt_loader.py          # Charge les prompts (repo first, vault override optionnel)

  utils/
    dedup.py                  # Anti-doublon URL par fenetre temporelle (30s)
    paths.py                  # Slugify (safe_slug, vault_slug) + protection path traversal
    pricing.py                # Resolution dynamique des couts tokens via pricing.json
    token_logger.py           # Log usage tokens + cout estime par appel Claude

plugin/                       # Extension Firefox Manifest V3
  manifest.json               # Declaration extension (permissions, icones, scripts)
  icons/
    icon-48.png               # Icone toolbar 48px
    icon-96.png               # Icone haute resolution 96px
  background/
    service_worker.js         # Background script — extraction page, POST /analyze, gestion timeout
  content/
    extract.js                # Content script — extrait le texte propre de la page active
  popup/
    popup.html                # UI du popup (bouton, resultats, parametres)
    popup.js                  # Logique popup (analyse, config token/URL backend)
    popup.css                 # Styles du popup

tests/                        # pytest + pytest-asyncio
config.yaml                   # Config métier unique (vault + modèles LLM + serveur)
pyproject.toml                # Dependances et config projet (uv/hatch)
```

## Pipeline d'analyse

```
URL + contenu (plugin ou CLI)
  │
  ├─ Cache URL → deja analysee ? → skip (sauf --refresh)
  │
  ├─ Fetch fallback (si contenu < 200 chars)
  │
  ├─ [parallele]
  │    ├─ Analyse offre (Claude + docs perso) → AnalysisResult
  │    └─ Capture PDF (Playwright, best-effort)
  │
  ├─ Cache entite → fiche entreprise existe ? → skip (sauf --refresh)
  │    └─ sinon : CompanyAnalyzer (Claude + Brave Search) → rapport
  │
  ├─ Score gate → decision + chanceRating
  │    └─ si GO : [parallele]
  │         ├─ Generation lettre de motivation (LLM)
  │         └─ Generation outreach (LLM) → LinkedIn, email, suggestions CV
  │
  └─ Ecriture vault Obsidian
       ├─ {slug}.offre.md      (contenu brut + frontmatter)
       ├─ {slug}.analyse.md    (scoring + recommandations)
       ├─ {slug}.lettre.md     (lettre + accroche LinkedIn + email intro + suggestions CV)
       ├─ {slug}.pdf           (si capture reussie)
       └─ 02_Companies/{entreprise}.md (si nouvelle)
```

## Caches

| Cache | Cle | Comportement |
|-------|-----|--------------|
| URL | `url` dans frontmatter `*.offre.md` | Skip total si deja analysee. Override : `--refresh` |
| Entite | `02_Companies/{slug}.md` | Skip CompanyAnalyzer si fichier existe. Override : `--refresh` |
| Docs perso | `cache_control: ephemeral` (API Anthropic) | Automatique selon flag `cache` dans `config.yaml` > vault.personal_docs |
