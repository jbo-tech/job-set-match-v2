# Status

## Objectif
Outil personnel de veille emploi : capture d'offre depuis Firefox → analyse Claude (offre + entreprise + profil) → dossier structuré dans vault Obsidian → dashboard via Obsidian Bases.

## Focus actuel
Direction 2 (prompting lettre) et Direction 4 (outreach LinkedIn/email/CV) implémentées. 140 tests passent. Few-shot dynamique abandonné. Prompts dans le repo (source de vérité). Prochaines étapes : tests manuels E2E, calibrage.

## Log

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
- Next : test E2E complet (analyser une vraie offre et vérifier les 4 artefacts : analyse, lettre, outreach, rapport entreprise). Calibrer la qualité du nouveau prompt lettre vs l'ancien. Vérifier que le prompt outreach produit du LinkedIn utilisable (280 chars). Direction 5 (prep entretien) reste disponible.

### 2026-05-23
- Done: Abstraction LLM multi-provider complète.
  - **Module `app/llm/`** : `LLMClient` Protocol + `AnthropicLLMClient` (prompt cache préservé) + `OpenAILLMClient` (couvre GPT, Mistral, Groq, DeepSeek, Gemini via `base_url`) + factory par préfixe model_id.
  - **Config** : `ANALYSIS_MODEL`, `COMPANY_MODEL`, `GENERATION_MODEL` par service (fallback `DEFAULT_MODEL`). API keys par provider (`OPENAI_API_KEY`, `MISTRAL_API_KEY`, `DEEPSEEK_API_KEY`, `GROQ_API_KEY`, `GOOGLE_API_KEY`).
  - **Migration services** : OfferAnalyzer, CompanyAnalyzer, CoverLetterGenerator découplés du SDK Anthropic, reçoivent chacun leur `LLMClient`.
  - **Tool use abstraction** : `format_assistant_message()` + `format_tool_results()` sur le Protocol — CompanyAnalyzer provider-agnostic (plus de isinstance checks).
  - **Fix token_logger** : `log_usage()` reçoit le `model_id` réel (plus de résolution via `settings.default_model` — bug latent corrigé).
  - **DocumentLoader** : nouveau `build_system_text()` pour providers non-Anthropic (flatten des blocks en texte).
  - **Dépendance** : `openai>=1.0` ajoutée à pyproject.toml.
- Tests : 119/119 passent (+31 net vs session précédente).
- Problèmes : aucun bloquant.
- Next : directions /explore restantes — prompting lettre (ton), few-shot candidatures validées, prep entretien, accroche LinkedIn/email.

### 2026-05-22
- Done: Audit complet du codebase (sécurité, optim, homogénéité, robustesse, maintenabilité) suivi d'un plan en 6 groupes et implémentation de tous les 15 items actionnables.
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
