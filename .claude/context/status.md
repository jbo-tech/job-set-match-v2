# Status

## Objectif
Outil personnel de veille emploi : capture d'offre depuis Firefox → analyse Claude (offre + entreprise + profil) → dossier structuré dans vault Obsidian → dashboard via Obsidian Bases.

## Focus actuel
Durcissement et distribution du plugin terminés. **Prochaine étape = test E2E manuel** (jamais lancé depuis avril) : vraie analyse plugin→backend→vault, vérifier le frontmatter `.analyse.md`, puis itérer sur `app/prompts/analysis.py` + `--refresh` pour comparer les versions de prompt.

## Log

### 2026-06-18
- Done: **Distribution & durcissement du plugin** (lot non commité).
  - **Voie A retenue contre Automa** : garder le plugin custom (privilèges minimaux) + signature **unlisted** AMO. Nouveau `plugin/sign.sh` (identifiants via env `WEB_EXT_API_KEY`/`WEB_EXT_API_SECRET`), section README, `.gitignore` (`.claude/delegate-auto`).
  - **Audit du plugin** → scope des points 🟡 → implémentation de 4 corrections :
    - Bouton « Ré-analyser quand même » (deduplicated → `refresh:true` propagé au backend).
    - `extract.js` troncature 15 000 → 50 000 (alignée sur `AnalyzeRequest.content`).
    - `auth.py` : 401 → `{"error": ...}` (cohérent API, lu par le service worker) + `tests/test_auth.py`.
    - Plugin **loopback-only** : rejet host ≠ `127.0.0.1`, suppression `url-warning` (+ nettoyage CSS `.hidden`/`.url-warning`).
  - **Point 2 écarté** après lecture de `pipeline.py:181` : le backend ne perd jamais le contenu plugin → modif inutile.
  - `/document` régénéré (`architecture.md` + `reference.md`, stamp `e12a4e8`).
- Tests : **158/158** (+3, test_auth).
- Auto-délégation activée (`/delegate-on`) ; lot fait en direct car touche `auth.py` (sensible) + contrat plugin↔backend.
- Next : test E2E manuel ; commit du lot (`feat(plugin): re-analyze button, loopback-only backend, consistent auth error`).

### 2026-06-15
- Done: **Fallback chromium système dans `install.sh`** — Playwright 1.58 ne fournit pas de build Chromium pour Ubuntu 26.04.
  - **`install.sh`** : tente `uv run playwright install chromium`, en cas d'échec cherche un chromium système (snap, apt, chrome, brave, edge) et configure `PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH` dans `.env`. Si rien trouvé, instructions (`sudo snap install chromium`).
  - **`app/services/content_fetcher.py`** : lit `PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH` et le passe en `executable_path` à `chromium.launch()` si défini. Ajout `import os`.
  - **`.env.example`** : documente la nouvelle variable.
- Tests : 155/155 passent.
- À noter : `docs/` (stamp `f71ead4`) périmé — 2 fichiers modifiés depuis (content_fetcher, config). Re-`/document` à prévoir.
- Next : test E2E manuel (B) — toujours pas lancé.

### 2026-06-06
- Done: Feature **A — attribution des analyses par version de prompt** (commit `f71ead4`).
  - **`app/utils/prompt_version.py`** (nouveau) : `prompt_fingerprint(text)` = sha256[:8] du prompt. Version **automatique** (change dès que le prompt change, zéro maintenance).
  - **`pipeline.py`** : stocke `analysis_prompt_version` / `analysis_model` / `analysis_temperature` en `__init__` ; capture le **coût de l'analyse seule** (delta `cost_usd` juste après `_analyze_and_capture`) ; passe `analysis_meta` au writer.
  - **`obsidian_writer.py`** : param optionnel `analysis_meta` → ajoute `prompt_version` / `model` / `temperature` / `cost_usd` au frontmatter `.analyse.md`.
  - **Insight produit-clé** : ne pas optimiser sur les scores auto-attribués par le LLM (auto-flatterie possible) — le signal de qualité réel est le `status` (issue humaine). Cf. anti-pattern + décision.
- Tests : 155/155 (+5).
- Next : test E2E manuel (B).

### 2026-06-05
- Done: `/document` (génération docs d'orientation) → `/scope` → `/goal` (nettoyage drift).
  - **`docs/architecture.md`** + **`docs/reference.md`** créés (stamp commit `1e5f687`).
  - **Drift corrigé (D1–D5)** : commentaires échelle seuil (0-100→1-10), liens CLAUDE.md repointés, max_tokens_outreach configurable, README nettoyé, note ASCII token ajoutée à .env.example.
- Tests : 150/150 passent.
- Next : commit + test E2E manuel.

### 2026-06-04
- Done: Audit général → scope → implémentation durcissement sécurité.
  - SSRF redirections (`content_fetcher.py`) : `follow_redirects=False` + boucle revalidation par saut.
  - SSRF Playwright : `_guard_route` câblé via `context.route`.
  - Plugin : port 8001→8000, token non-ASCII rejeté à la saisie, commentaire obsolète supprimé.
  - `AnalyzeRequest.content` max_length=50_000 verrouillé par tests.
- Tests : 150/150 (+10).
- Next : test E2E manuel.

### 2026-05-26
- Done: Documentation de la configuration multi-provider (README + config.example.yaml).
- Next : test E2E manuel.

### 2026-05-26 (plus tôt)
- Done: Homogénéisation config — `config.yaml` unique (vault + LLM + serveur), `.env` secrets only.
- Tests : 140/140.
- Next : test E2E manuel.

### 2026-05-24
- Done: Direction 2 (prompting lettre) + Direction 4 (outreach) + revert prompts vers le repo.
- Tests : 140/140 (+21).
- Next : test E2E complet.

### 2026-05-23
- Done: Abstraction LLM multi-provider complète.
- Tests : 119/119 (+31).
- Next : directions /explore restantes.

### 2026-05-22
- Done: Audit complet + 15 items actionnables.
- Tests : 88/88 (+25).

### 2026-05-20
- Done: Fix plugin Firefox, cache entité, flag --refresh, tests complémentaires, README.md complet.
- Tests : 63/63 (+9).

### 2026-05-19
- Done: audit infra-expert, quick fixes sécurité, ObsidianWriter R2, pricing dynamique, fix CompanyAnalyzer.
- Tests : 54/54 (+12).

### 2026-05-14
- Done: §6.0–§6.2, §6.5 vault_layout, document_loader, build_system_blocks.
- Tests : 42/42.

### 2026-04-13
- Done: Phase 3 (tests), Phase 4 (cover letter), Phase 1 (plugin Firefox), Phase 5 guide.
- Tests : 42/42.

### 2026-04-10
- Bootstrap : contexte projet initialisé, phases 0–3.5 complétées.
