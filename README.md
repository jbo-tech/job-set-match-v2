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
# Optionnel : BRAVE_API_KEY, SCORE_THRESHOLD, DEFAULT_MODEL
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

## Configuration (.env)

| Variable | Description | Defaut |
|----------|-------------|--------|
| `OBSIDIAN_VAULT_PATH` | Chemin absolu vers le vault Obsidian | *requis* |
| `ANTHROPIC_API_KEY` | Cle API Anthropic | *requis* |
| `AUTH_TOKEN` | Token d'authentification pour le plugin | *requis* |
| `BRAVE_API_KEY` | Cle API Brave Search (analyse entreprise) | *(vide = desactive)* |
| `SCORE_THRESHOLD` | Seuil minimum de `chanceRating` pour generer la lettre (0 = decision Claude seule) | `0.0` |
| `DEFAULT_MODEL` | Modele Claude a utiliser | `claude-sonnet-4-20250514` |
| `MAX_TOKENS` | Tokens max par reponse Claude | `8192` |
| `ANALYSIS_TEMPERATURE` | Temperature pour l'analyse | `0.2` |
| `GENERATION_TEMPERATURE` | Temperature pour la lettre | `0.7` |

## Structure du projet

```
app/                          # Backend FastAPI + logique metier
  config.py                   # Pydantic Settings — charge .env, expose les parametres
  main.py                     # Point d'entree FastAPI (/analyze, /health) + mode CLI
  models.py                   # Schemas Pydantic — contrats partages (request, response, analyse)
  pipeline.py                 # Orchestrateur central — enchaine les etapes d'analyse
  vault_layout.py             # Parse vault_layout.yaml — structure du vault Obsidian

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
vault_layout.yaml             # Config structure vault Obsidian (chemins, docs perso, flags cache)
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
| Docs perso | `cache_control: ephemeral` (API Anthropic) | Automatique selon flag `cache` dans `vault_layout.yaml` |
