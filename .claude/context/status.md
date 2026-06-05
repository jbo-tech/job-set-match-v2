# Status

## Objectif
Outil personnel de veille emploi : capture d'offre depuis Firefox → analyse Claude (offre + entreprise + profil) → dossier structuré dans vault Obsidian → dashboard via Obsidian Bases.

## Focus actuel
Durcissement sécurité post-audit (SSRF redirections, cohérences plugin). Prochaine étape : test E2E manuel pour valider la lecture de `config.yaml` en conditions réelles + valider le plugin avec un vrai Chromium (le guard navigation Playwright n'est testé qu'unitairement).

## Log

### 2026-06-04
- Done: Audit général (`/audit`) → scope (`/scope`) → implémentation (`/goal`) d'un lot de durcissement sécurité.
  - **SSRF redirections (#1, `content_fetcher.py`)** : `fetch_clean_text` passe en `follow_redirects=False` + boucle manuelle qui revalide CHAQUE saut via `_validate_url` avant le `get` (cap `MAX_REDIRECTS=5`). Bloque le vecteur « URL publique → 302 → IP interne » avant la connexion. Résolution des `Location` relatives via `httpx.URL().join()`.
  - **SSRF Playwright (#1)** : nouveau `_guard_route` câblé via `context.route("**/*", ...)` — avorte les requêtes de navigation vers un hôte interne (redirections HTTP/JS), avant connexion. Sous-ressources non revalidées (coût DNS).
  - **DNS rebinding (#2)** : documenté comme limite assumée dans la docstring `_validate_url` (non codé — fermer imposerait un transport httpx custom forçant l'IP validée).
  - **Plugin** : placeholder port `8001`→`8000` (popup.html) ; `checkUrlWarning` ne traite plus `localhost` comme local sûr (cohérent avec `host_permissions` 127.0.0.1 only) ; token non-ASCII **rejeté à la saisie** avec message explicite au lieu d'être muté silencieusement (popup.js) ; `getAuthToken` ne mute plus (service_worker.js) ; commentaire obsolète « storage.local fallback » supprimé.
  - **#8** : `AnalyzeRequest.content` avait déjà `max_length=50_000` → verrouillé par `tests/test_models.py` (nouveau).
- Tests : 150/150 passent (+10 net : 5 redirections SSRF, 3 guard Playwright, 2 borne content).
- Problèmes : `.env.example` toujours inaccessible (permissions `.env*`) → note ASCII token non ajoutée à `.env.example` (contrainte appliquée dans le code). Lint préexistant `F541` ligne 308 de test_content_fetcher.py laissé tel quel (hors scope).
- Next : test E2E manuel (offre réelle + config.yaml) ; valider le guard Playwright avec un vrai Chromium.

### 2026-05-26
- Done: Documentation de la configuration multi-provider.
  - **README.md** : nouvelle sous-section "Modèles multi-provider" avec tableau des préfixes/providers/clés API et exemple de configuration mixte.
  - **README.md** : descriptions enrichies pour `temperatures` (rôle par tâche : cohérence vs style), `max_tokens` et `score_threshold` (seuil chanceRating 0-100).
  - **config.example.yaml** : commentaires ajoutés sur la section `llm.models` (préfixes supportés, providers, exemples), la section `temperatures` (explication par tâche), `max_tokens` et `score_threshold`.
  - **`llm.models.*`** : les champs d'override vides (`""`) tombent sur `default` ; un champ non-vide surcharge le modèle pour la tâche correspondante.
- Next : test E2E manuel (analyser une vraie offre, vérifier que `config.yaml` est bien lu et que les overrides de modèles fonctionnent).

### 2026-05-26 (plus tôt)
- Done: Homogénéisation complète de la configuration — fusion de `vault_layout.yaml` et config métier du `.env` dans un seul `config.yaml`.
  - **Nouveau `config.yaml`** : sections `vault` (anciennement `vault_layout.yaml`), `llm` (modèles par tâche avec fallback, températures, max_tokens), `server` (score_threshold, host, port).
  - **`.env.example` allégé** : uniquement les secrets (API keys, AUTH_TOKEN). `config.yaml` ajouté à `.gitignore` ; `config.example.yaml` sert de template versionné.
  - **`app/config.py` refactoré** : `Settings` (BaseSettings) = secrets ; `AppConfig` (BaseModel) = métier. `LLMModelsConfig.resolve()` remplace `settings.resolve_model()`. Chemin `config.yaml` résolu depuis le package root (plus de dépendance au `cwd`).
  - **`app/vault_layout.py`** : `get_vault_layout()` redirige vers `get_app_config().vault` (backward compat préservée). Import local pour éviter le circulaire avec `app.config`.
  - **`app/pipeline.py` / `app/main.py` / `app/utils/token_logger.py`** : basculés sur `get_app_config()`.
  - **Tests** : `tests/conftest.py` avec fixture `app_config` (vault temporaire, déterministe). `tests/test_pipeline.py` et `tests/test_llm.py` mis à jour. Imports et helpers morts nettoyés.
  - **Doc** : `README.md` et `CLAUDE.md` mis à jour (`server` au lieu de `app`, `outreach` documenté).
- Tests : 140/140 passent.
- Problèmes : accès Read/Bash bloqué sur `.env.example` (contourné via `python3 -c`). Import circulaire `app.config` ↔ `app.vault_layout` résolu par import local.
- Next : test E2E manuel.

### 2026-05-24
- Done: Direction 2 (prompting lettre) + Direction 4 (outreach) + revert prompts vers le repo.
  - **Prompting lettre (Direction 2)** :
    - `vault_layout.yaml` : `applications: 03_Applications` (aligné avec vault réel), `personnalite` ajouté à `personal_docs` (cacheable), section `prompts` documentée mais commentée (override optionnel).
    - `app/vault_layout.py` : champ `prompts: dict[str, str]` + méthode `resolve_prompt()` sur `VaultLayout`.
    - `app/services/prompt_loader.py` (nouveau) : charge prompts depuis vault (override) ou Python (fallback). Strip frontmatter/heading/code fences.
    - `app/prompts/generation.py` : réécrit en français, 1 exemple (Beta.gouv DIALOG), directives de ton issues de Personnalite.md, ancres narratives, pièges à éviter, source control préservé.
    - Services (`OfferAnalyzer`, `CompanyAnalyzer`, `CoverLetterGenerator`) : reçoivent `prompt: str` par constructeur au lieu d'importer depuis `app/prompts/`. Pipeline passe les prompts via `PromptLoader`.
  - **Outreach (Direction 4)** :
    - `app/prompts/outreach.py` (nouveau) : prompt pour accroche LinkedIn (280 chars), email intro (80-120 mots), suggestions CV (mots-clés, expériences, compétences, ajustements).
    - `app/models.py` : `OutreachResult`, `EmailIntroduction`, `CvSuggestions`.
    - `app/services/outreach_generator.py` (nouveau) : LLM → JSON structuré, même pattern que CoverLetterGenerator.
    - `app/pipeline.py` : lettre + outreach en parallèle (`asyncio.gather`), même condition (decision=true).
    - `app/services/obsidian_writer.py` : `.lettre.md` enrichi → "Candidature" avec sections : lettre de motivation, accroche LinkedIn, email d'introduction, suggestions CV.
  - **Revert prompts** : prompts dans le repo (source de vérité), vault comme override optionnel. `app/prompts/` reste le package canonique.
  - **Abandon** : Direction 3 (few-shot dynamique) abandonnée.
- Tests : 140/140 passent (+21 net vs session précédente).
- Problèmes : aucun bloquant.
- Next : test E2E complet.

### 2026-05-23
- Done: Abstraction LLM multi-provider complète.
- Tests : 119/119 passent (+31 net vs session précédente).
- Next : directions /explore restantes.

### 2026-05-22
- Done: Audit complet du codebase + implémentation de tous les 15 items actionnables.
- Tests : 88/88 passent (+25 net vs session précédente).

### 2026-05-20
- Done: Fix bug plugin Firefox, §6.4 cache entité, §6.6 flag --refresh, §6.7 tests complémentaires, plugin améliorations, README.md complet.
- Tests : 63/63 passent (+9 net vs session précédente).

### 2026-05-19
- Done: audit infra-expert, quick fixes sécurité, §6.3 ObsidianWriter R2, pricing dynamique, fix CompanyAnalyzer.
- Tests : 54/54 passent (+12 net vs session précédente).

### 2026-05-14
- Done: §6.0–§6.2, §6.5 vault_layout, document_loader, build_system_blocks.
- Tests : 42/42 passent.

### 2026-04-13
- Done: Phase 3 (tests), Phase 4 (cover letter), Phase 1 (plugin Firefox), Phase 5 guide.
- Tests : 42/42 passent.

### 2026-04-10
- Bootstrap : contexte projet initialisé, phases 0–3.5 complétées.
