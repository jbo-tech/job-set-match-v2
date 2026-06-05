# Référentiel — Job Set & Match V2

> Ce que le code fait réellement (surface publique), et les **écarts** avec
> l'intention enregistrée (`.claude/context/decisions.md`). Carte pédagogique :
> [architecture.md](./architecture.md). Install/usage : [README](../README.md).

## Drift — à arbitrer

Écarts entre intention et code/docs. Liste = ta to-do d'arbitrage.

| # | Type | Quoi | Où regarder | Question |
|---|---|---|---|---|
| D1 | Doc ⇄ code | `score_threshold` documenté « (0-100) » alors que `chanceRating` est sur **1-10** (prompt) et que le seuil est comparé tel quel. Un seuil « 50 » ne déclencherait jamais la lettre. | `config.yaml` (commentaire), `README.md:99`, [_should_generate_letter](#config-clés-qui-comptent), `app/prompts/analysis.py:40-66` | Corriger les commentaires en « 0-10 », ou changer l'échelle ? |
| D2 | Rule ⇄ absent | La section *Context* de `CLAUDE.md` renvoie à `V2_PLAN.md` et `APP_INTEGRATION_SPEC.md` qui **n'existent plus** à la racine. | `CLAUDE.md` (section ## Context) | Supprimer ces renvois, ou restaurer/retrouver les fichiers ? |
| D3 | Doc stale | `README.md:28` liste `SCORE_THRESHOLD` et `DEFAULT_MODEL` comme variables `.env` optionnelles — c'était avant l'unification config ; elles vivent désormais dans `config.yaml`. Contredit `README.md:70`. | `README.md:28` | Retirer ces deux clés de l'exemple `.env`. |
| D4 | Intent non appliqué | Le token doit être ASCII (imposé par le code + décision 2026-06-04), mais `.env.example` ne le documente pas. Fichier inaccessible aux outils (permissions `.env*`). | `.env.example` | Ajouter manuellement une note « AUTH_TOKEN : ASCII uniquement ». |
| D5 | Choix non tracé | `OutreachGenerator` reçoit `max_tokens=4096` **codé en dur** dans le pipeline, alors que tous les autres services utilisent `llm.max_tokens` (8192). | `app/pipeline.py:80` | Intentionnel (sortie courte) ou oubli ? Sinon exposer en config. |
| D6 | Choix non tracé (mineur) | `CompanyAnalyzer` utilise `temperatures.get("analysis", 0.2)` — il n'existe pas de clé `company` ; il réutilise la temp d'analyse sans décision dédiée. | `app/pipeline.py:67`, `config.yaml` (section `temperatures`) | Ajouter une clé `company`, ou documenter le partage ? |
| D7 | Cosmétique | Import dupliqué : `from app.models import OutreachResult` (ligne 24) en plus du groupe ligne 19. | `app/pipeline.py:19,24` | Fusionner (sans impact fonctionnel). |

**Docs en place** : aucun autre fichier `docs/` que `architecture.md` et ce
référentiel (ils viennent d'être créés). Les specs `V2_PLAN.md` /
`APP_INTEGRATION_SPEC.md` ne sont plus présentes (cf. D2). Rien à fusionner ni à
supprimer pour l'instant.

Hors de ces points, le code est **aligné** sur les décisions enregistrées — y
compris la limite DNS rebinding, explicitement assumée (décision « Anti-SSRF :
revalidation par saut » + docstring `_validate_url`), donc *pas* un drift.

---

## Surface par composant

### Points d'entrée HTTP (`app/main.py`)

| Route | Auth | Entrée → Sortie | Notes |
|---|---|---|---|
| `GET /health` | non | — → `{"status":"ok"}` | Chemin public (`PUBLIC_PATHS`). |
| `GET /stats` | oui | — → compteurs tokens/coût session | Stats process-globales (`token_logger`), pas par-requête. |
| `POST /analyze` | oui | `AnalyzeRequest` → `AnalyzeResponse` | Sérialisé par un `Semaphore(1)` : **une analyse à la fois**. Dédup URL en mémoire (fenêtre 30 s) avant le pipeline. |

`AnalyzeRequest` : `url: HttpUrl`, `title: str`, `content: str` (**max 50 000**,
verrouillé par test), `needs_fetch: bool`, `refresh: bool`.
`AnalyzeResponse` : `status` ∈ `success|deduplicated|error`, + champs synthèse
(`company`, `position`, `decision`, `score_total`, `chance_rating`, `cost_usd`,
`vault_path`, `error`).

**Gotcha** : `/stats` agrège la consommation depuis le démarrage du process ; le
coût d'une analyse isolée est calculé par diff dans `Pipeline.run` (`cost_before`).

### Point d'entrée CLI (`python -m app.main`)

```
python -m app.main <URL> [chemin/offre.txt] [--refresh] [--temperature 0.5]
echo "contenu" | python -m app.main <URL>
```
- Sans fichier → lit stdin. Contenu tronqué à `MAX_CLI_CONTENT` (50 000).
- `--temperature` n'affecte que la **génération** (lettre) : il copie l'`AppConfig`
  en profondeur pour ne pas polluer le cache `lru_cache` (décision « Pipeline
  accepte `app_config` optionnel »).
- Sortie : `AnalyzeResponse` en JSON indenté sur stdout.

### Orchestrateur (`app/pipeline.py`)

`Pipeline.run(request) -> AnalyzeResponse`. Enchaînement : fallback contenu →
(`gather` analyse offre ‖ capture PDF) → analyse entreprise (sauf fiche existante)
→ score gate → (`gather` lettre ‖ outreach si gate) → écriture vault.

- **Best-effort** : PDF, entreprise, lettre, outreach échouent silencieusement
  (loggés, `None`). Seule une `AnalysisError` (analyse offre) renvoie
  `status="error"`.
- **Dédup** : `_maybe_fetch_fallback` ne fetch que si `needs_fetch` ou contenu
  `< MIN_CONTENT_LENGTH` (200). `url_already_analyzed` / `company_exists`
  court-circuitent si `refresh` est faux.

### Services (`app/services/`)

| Service | Méthode publique | Comportement / gotcha |
|---|---|---|
| `OfferAnalyzer` | `analyze(content, url) -> AnalysisResult` | Un appel LLM → JSON structuré. Lève `AnalysisError` si parsing/échec → **fait échouer le pipeline**. |
| `CompanyAnalyzer` | `analyze(company_name) -> str \| None` | Boucle tool-use (`MAX_TOOL_ITERATIONS=5`) + Brave Search. Si la limite est atteinte, **appel final sans tools** pour forcer une synthèse (décision dédiée). |
| `CoverLetterGenerator` | `generate(analysis, offer_content) -> str` | Best-effort dans le pipeline. |
| `OutreachGenerator` | `generate(analysis, offer_content) -> OutreachResult` | Accroche LinkedIn + email + suggestions CV. ⚠ drift D5 : `max_tokens=4096` codé en dur côté pipeline. |
| `ContentFetcher` | `fetch_clean_text(url) -> str \| None` ; `capture_pdf(url) -> bytes \| None` | Anti-SSRF : `_validate_url` par **saut** (httpx `follow_redirects=False`, `MAX_REDIRECTS=5`) ; Playwright filtré par `_guard_route`. Limite DNS rebinding assumée. Browser Playwright lazy + persistant. |
| `DocumentLoader` | `load() -> dict[str,str]` | Charge les docs perso du vault (glob), produit des blocs système ; honore le flag `cache` par doc. |
| `ObsidianWriter` | `write(...) -> Path` ; `company_exists` ; `url_already_analyzed` | Slug `Entreprise - Poste - Date` ; suffixe hash si `unknown`. `ensure_within` garde-fou path traversal. |
| `BraveSearch` | (outil du CompanyAnalyzer) | Client REST httpx ; `BraveSearchError`. Désactivé si `BRAVE_API_KEY` vide. |
| `PromptLoader` | `load(key) -> str` | Vault (override) sinon constante Python. En pratique : constantes Python (section `prompts` vide). |

### Couche LLM (`app/llm/`)

- `create_llm_client(model_id, api_keys) -> LLMClient` : route par **préfixe**
  (`_PROVIDER_REGISTRY`). `claude-*` → `AnthropicLLMClient` ; `gpt-/o1-/o3-/o4-/chatgpt-`,
  `mistral`, `deepseek`, `groq/`, `gemini` → `OpenAILLMClient` (base_url adaptée ;
  `groq/` strippé). Clé API manquante → `ValueError` au démarrage.
- `LLMClient` (Protocol) : `complete(...)`, `complete_with_tools(...)`,
  `format_assistant_message`, `format_tool_results`. Les deux derniers encapsulent
  les formats tool-use divergents Anthropic (content blocks) vs OpenAI
  (function calling) — décision « format_* sur le Protocol, pas dans les services ».
- `system_blocks` (cache_control Anthropic) : utilisés par le client Anthropic,
  aplatis en texte système par les autres.

### Config — clés qui comptent

Secrets (`.env`, via `Settings`) : `ANTHROPIC_API_KEY` (obligatoire), `AUTH_TOKEN`
(obligatoire, **ASCII** — cf. D4), `BRAVE_API_KEY` + clés providers optionnelles.

Métier (`config.yaml`, via `AppConfig`) :

| Section | Clé | Contrôle |
|---|---|---|
| `vault` | `vault_root`, `paths`, `personal_docs`, `prompts` | Racine vault, dossiers, docs perso (cacheables), override prompts. |
| `llm` | `models.{default,analysis,company,generation,outreach}` | Modèle par service ; vide → `default`. Préfixe → provider. |
| `llm` | `temperatures.{analysis,generation,outreach}` | Température par tâche. ⚠ D6 : pas de clé `company` (réutilise `analysis`). |
| `llm` | `max_tokens` | 8192 par défaut (⚠ D5 : outreach ignore cette valeur). |
| `server` | `score_threshold` | Seuil sur `chanceRating`. **⚠ D1 : échelle réelle 1-10, pas 0-100.** `0.0` = toujours générer. |
| `server` | `host`, `port` | Bind serveur (défaut `127.0.0.1:8000`). |

**Résolution** : `LLMModelsConfig.resolve(service)` → override ou `default`.
`get_app_config()` est en `lru_cache` ; le mode CLI le copie pour l'override de
température.

### Plugin Firefox (`plugin/`)

- `extract.js` : nettoie la page (retire nav/footer/scripts), `body.innerText`,
  tronque à 15 000, `needsFetch` si `< 200` chars.
- `service_worker.js` : `POST {backendUrl}/analyze` avec `X-Auth-Token`. Default
  `http://127.0.0.1:8000`, timeout 120 s. Token relu **sans mutation**.
- `popup.js` : config `backendUrl` + `authToken` dans `storage.local`. Token
  **non-ASCII rejeté** à la saisie (message explicite). `localhost` déclenche
  l'avertissement « URL non locale » (seul `127.0.0.1` est dans `host_permissions`).
