# Decisions

Décisions techniques et leur contexte. Ajoutés via `/retro`.

### FastAPI comme backend
**Decision** : FastAPI plutôt qu'un script CLI
**Context** : nécessaire pour recevoir les POST du plugin Firefox, async natif
**Alternatives** : CLI + bookmarklet, Flask
**Date** : inférée du plan V2

### Obsidian comme storage et UI
**Decision** : écriture directe dans le vault Obsidian (pathlib), dashboard via Obsidian Bases
**Context** : supprime le besoin d'une UI custom (Streamlit V1 était du surpoids), le vault est un dossier sur disque
**Alternatives** : Streamlit, base de données + UI web
**Date** : inférée du plan V2

### Claude API avec tool_use pour les MCPs
**Decision** : Anthropic SDK avec tool_use (Fetch MCP, Screenshot MCP, Brave Search MCP)
**Context** : MCPs fournissent fetch propre, capture archival, recherche entreprise sans dev custom
**Alternatives** : appels API directs, scraping maison
**Date** : inférée du plan V2

### Plugin Firefox Manifest V3
**Decision** : plugin Firefox natif pour capturer les offres (y compris pages authentifiées)
**Context** : accès au DOM de la page → extraction même derrière un login (LinkedIn, WTTJ)
**Alternatives** : Automa (MVP rapide), bookmarklet (pas d'accès auth)
**Date** : inférée du plan V2

### Appels Python directs vs MCP servers
**Decision** : remplacer les MCP servers (Fetch, Screenshot, Brave Search) par des appels Python directs (httpx + bs4, Playwright, httpx REST)
**Context** : MCP ajoute 3 processus externes à gérer, un bus JSON-RPC, et de la latence. Les libs Python font la même chose en 50 lignes chacune. Claude tool_use est conservé uniquement pour CompanyAnalyzer (Brave Search en boucle pilotée par Claude).
**Alternatives** : MCP servers npm (plan initial)
**Date** : 2026-04-13

### PDF via Playwright vs PNG screenshot
**Decision** : capture archivale en PDF (Playwright `page.pdf()`) plutôt que PNG
**Context** : les offres sont souvent multi-pages → PNG nécessiterait du scrolling + stitching complexe. PDF natif Chromium gère le multi-page nativement, format A4 + marges 1cm. Limitation : Playwright n'accède pas aux sessions Firefox → la capture est la version publique de la page (best-effort).
**Alternatives** : PNG (capture viewport unique ou scrolling), imprimé HTML
**Date** : 2026-04-13

### CoverLetter best-effort dans le pipeline
**Decision** : la génération de lettre est best-effort (try/except → None, pipeline continue sans lettre)
**Context** : cohérent avec CompanyAnalyzer et capture PDF. L'analyse (analyse.md) est le livrable critique, les artefacts secondaires ne doivent pas bloquer.
**Alternatives** : fail fast si la lettre échoue
**Date** : 2026-04-13

### vault_layout.yaml — config externalisée avec path unique acceptant wildcards
**Decision** : `vault_layout.yaml` à la racine du repo déclare `vault_root`, `paths` (applications/companies/archive) et `personal_docs`. Chaque `personal_docs.{key}` a un champ `path` unique qui accepte les motifs glob (`*`, `?`, `[!_]`). Le loader détecte les wildcards en runtime et lance la résolution glob, sinon traite comme fichier unique.
**Context** : Le vault a évolué — `experiences` n'est plus un fichier monolithique mais un dossier de 5 fichiers (split par poste). Forcer 2 champs distincts (`path` vs `glob`) serait verbeux ; obliger une liste pour 1 fichier (`paths: [...]`) serait du sur-typage. Le caractère wildcard suffit comme signal de mode.
**Alternatives** : champ `glob` dédié (plus explicite mais double l'API), `paths` toujours liste (verbeux).
**Date** : 2026-05-14

### score_chance vs score_succes — sémantique actée
**Decision** : `score_chance` = probabilité que la candidature soit retenue (vue externe : concurrence, fit profil/poste). `score_succes` = probabilité de réussir au poste après embauche (vue interne : capacité d'apprentissage, fit culture). Score total `/40` conservé (4 axes), aligne avec la grille V1.
**Context** : La spec APP_INTEGRATION_SPEC.md §7 listait les deux champs avec descriptions qui se chevauchaient (lignes 306-309). Risque de confusion à l'implémentation.
**Alternatives** : fusionner en un seul score (passer à `/30`, casse l'historique V1), inverser la sémantique.
**Date** : 2026-05-14

### DocumentLoader.build_system_blocks() — honore cache flag per-doc
**Decision** : `DocumentLoader.build_system_blocks(system_instruction)` construit la liste system Anthropic complète et split les docs en 2 blocs selon le flag `cache: true/false` du vault_layout : 1 bloc XML cacheable avec `cache_control: ephemeral` (cv/experiences/pitch/profil), 1 bloc XML non-cacheable (questions clés). Le breakpoint cache Claude est placé après le bloc cacheable, garantissant la mise en cache du contenu fixe.
**Context** : `questions` (Questions clés) varie peu mais ne vaut pas un cache breakpoint dédié (l'API Claude a un max de 4 breakpoints). Le flag `cache: false` permet de l'injecter sans le mettre en cache. Le code V1 plaçait tous les docs dans un seul bloc cacheable, ce qui contredisait l'intention du flag.
**Alternatives** : Garder tout dans un seul bloc (ignorer le flag), faire 5 blocs individuels (consomme tous les breakpoints), template Python avec placeholders `{cv}`, `{experiences}` (refonte plus invasive des prompts).
**Date** : 2026-05-14

### Helper transitoire pour refactor avec callers
**Decision** : Lors d'un refactor d'API publique consommée par des callers (ex: `DocumentLoader.load() -> str` → `dict[str, str]`), introduire un helper de compat temporaire (`load_xml()`) qui préserve l'ancien comportement le temps de migrer les callers. Marquer le code transitoire avec `TODO §6.X` pour piloter le retrait.
**Context** : Permet un refactor en 2 sessions sans laisser le code dans un état cassé entre deux. Évite le "big bang" refactor où on doit tout faire d'un coup.
**Alternatives** : Big bang refactor (risqué sur du code prod), garder l'ancienne API (dette qui s'accumule).
**Date** : 2026-05-14

### Pricing dynamique via pricing.json (LiteLLM)
**Decision** : résolution des coûts par token via `pricing.json` (vendored LiteLLM, partagé avec llm-sparring) au lieu de coûts hardcodés dans `config.py`. Module `app/utils/pricing.py` avec cascade : lookup exact model_id → substring match → fallback conservateur.
**Context** : les coûts hardcodés ($3/M input, $15/M output) ne tenaient pas compte du cache (cache_read à $0.30/M, cache_write à $3.75/M). Le fichier `pricing.json` du projet llm-sparring contient déjà tous les modèles avec cache pricing. Mutualiser évite de maintenir les prix manuellement.
**Alternatives** : hardcoder les 4 tarifs dans config.py (fragile si changement de modèle), appeler l'API Anthropic pour les prix (n'existe pas).
**Date** : 2026-05-19

### CompanyAnalyzer — appel final sans tools quand limite atteinte
**Decision** : quand la boucle tool_use atteint MAX_TOOL_ITERATIONS (8), au lieu de retourner `None`, faire un appel final sans tools avec un message demandant à Claude de produire le rapport avec les informations collectées.
**Context** : le premier test E2E sur une entité gouvernementale (MEFSIN) a montré que Claude cherchait indéfiniment sans conclure. Le `None` silencieux privait le vault d'un rapport entreprise pourtant partiellement collecté.
**Alternatives** : augmenter MAX_TOOL_ITERATIONS (coûteux, ne résout pas le fond), extraire le texte de la dernière réponse (incomplet, mélangé avec des tool_use blocks).
**Date** : 2026-05-19

### vault_slug — préserver espaces et accents pour Obsidian
**Decision** : la fonction `vault_slug()` (dans `app/utils/paths.py`) préserve espaces, accents et parenthèses dans les noms de fichiers. Seuls les caractères FS interdits sont remplacés (`/` → `_`, `:` → `-`, `\` → `_`, `|` → `-`, `*` → `_`, `?<>`" retirés). L'ancienne `safe_slug()` (python-slugify, ASCII, tirets) est conservée pour d'éventuels besoins hors vault.
**Context** : Obsidian gère bien les noms de fichiers avec espaces et accents. Le slug `Société Générale - Data Engineer - 2026-04-22` est plus lisible que `Societe-Generale-Data-Engineer-2026-04-22` dans le vault. Aligné avec la convention définie dans APP_INTEGRATION_SPEC.md §3.
**Alternatives** : ASCII-only (safe_slug existant — moins lisible dans le vault), URL-encoding (inutilement complexe).
**Date** : 2026-05-19

### Cache entité — skip CompanyAnalyzer si fiche existe
**Decision** : vérifier `02_Companies/{vault_slug(company)}.md` avant d'appeler CompanyAnalyzer. Si le fichier existe, skip l'analyse Brave+Claude. Bypass via `--refresh`.
**Context** : chaque appel CompanyAnalyzer coûte 3-9 appels API (Brave+Claude en boucle). Pour une même entreprise vue dans plusieurs offres, c'est du gaspillage. Le check fichier est instantané.
**Alternatives** : cache mémoire (perdu au redémarrage), toujours ré-analyser (coûteux).
**Date** : 2026-05-20

### Cache URL vérifié avant l'analyse offre
**Decision** : remonter le check `url_already_analyzed()` (étape 1.5) avant l'appel `OfferAnalyzer` (étape 2), au lieu de le faire après (ancien étape 3.5).
**Context** : si l'URL est déjà dans le vault, aucune raison de consommer un appel Claude pour l'analyse offre. Le scan des frontmatter coûte quelques ms vs 10-30s + tokens pour l'analyse.
**Alternatives** : garder le check après l'analyse (gaspillage API sur les doublons).
**Date** : 2026-05-20

### Port backend configurable dans le plugin
**Decision** : URL du backend stockée en `browser.storage.local` avec un champ dans le popup settings. Default `http://127.0.0.1:8000`. `host_permissions` élargi à `http://127.0.0.1/*`.
**Context** : le port 8000 peut être occupé par un autre processus. Hardcoder un port crée un couplage fragile entre le plugin et la config du serveur.
**Alternatives** : hardcoder le port (fragile), auto-découverte (over-engineering pour un outil local).
**Date** : 2026-05-20

### SSRF protection via DNS resolution + IP validation
**Decision** : `_validate_url()` dans content_fetcher vérifie le scheme (http/https uniquement) puis résout le DNS via `socket.getaddrinfo` (wrappé dans `run_in_executor`) et rejette les IPs privées/loopback/réservées/link-local via `ipaddress`. Appliqué avant `fetch_clean_text()` et `capture_pdf()`.
**Context** : l'URL vient du plugin Firefox (contrôlée par l'utilisateur). Un attaquant avec le token auth pourrait faire fetcher des URLs internes (169.254.x, 10.x, etc.). La résolution DNS empêche aussi le DNS rebinding.
**Alternatives** : simple regex sur l'URL (contournable par DNS rebinding), ne rien faire (acceptable pour un outil 100% local mais mauvaise hygiène).
**Date** : 2026-05-22

### Playwright browser persistant avec lazy-init
**Decision** : le browser Chromium est lancé une seule fois (lazy-init au premier `capture_pdf()`) et réutilisé. Chaque appel crée un nouveau context (léger). Crash recovery via `is_connected()`. Cleanup dans le lifespan FastAPI.
**Context** : `chromium.launch()` prend 2-5s et consomme ~200MB RAM. Relancer à chaque capture est du gaspillage. Les contexts sont jetables (isolés et peu coûteux).
**Alternatives** : lancer à chaque appel (ancien comportement, lent), pool de browsers (over-engineering pour semaphore=1).
**Date** : 2026-05-22

### CompanyAnalyzer — injection des docs perso via DocumentLoader
**Decision** : CompanyAnalyzer reçoit `DocumentLoader` en dépendance et injecte les docs perso via `build_system_blocks()` dans tous les appels Claude. Le prompt cache est activé (mêmes breakpoints que OfferAnalyzer et CoverLetterGenerator).
**Context** : sans docs perso, Claude analysait les entreprises sans connaître le profil du candidat. Les rapports n'étaient pas personnalisés (même rapport pour n'importe quel candidat). Le coût marginal est quasi-nul grâce au prompt cache.
**Alternatives** : ne pas injecter les docs (rapports génériques), résumer le profil en quelques lignes dans le prompt (perte de détail).
**Date** : 2026-05-22

### Pricing prefix match — longest key wins
**Decision** : remplacer le fuzzy match (`model_id in key or key in model_id`) par un prefix match bidirectionnel + sélection du match le plus long. Évite les faux positifs cross-modèle (ex: "opus" matchant "sonnet-4" par sous-chaîne).
**Context** : les model IDs Anthropic ont le format `claude-{family}-{version}-{date}`. Le config peut contenir une version sans date (`claude-sonnet-4`) ou avec (`claude-sonnet-4-20250514`). Le prefix match gère les deux cas sans ambiguïté.
**Alternatives** : regex avec extraction de famille/version (fragile), dict de mappings manuels (maintenabilité).
**Date** : 2026-05-22

### Abstraction LLM multi-provider — Protocol + 2 implémentations
**Decision** : `LLMClient` Protocol Python avec `AnthropicLLMClient` (SDK natif, prompt cache préservé) et `OpenAILLMClient` (SDK openai avec `base_url` configurable pour Mistral, Groq, DeepSeek, Gemini). Factory par préfixe model_id. Pas de LiteLLM.
**Context** : besoin de router différentes étapes du pipeline vers différents modèles/providers pour optimiser les coûts. LiteLLM est une dépendance lourde (~50 transitives) qui masque les spécificités providers. Le SDK openai suffit car la plupart des providers exposent un endpoint compatible. Anthropic gardé en natif pour le prompt cache (`cache_control: ephemeral`).
**Alternatives** : LiteLLM (lourd, magie), OpenRouter (intermédiaire, perd le cache), un seul SDK pour tout (impossible sans perte de features).
**Date** : 2026-05-23

### Tool use multi-provider — format_assistant_message + format_tool_results
**Decision** : les méthodes `format_assistant_message()` et `format_tool_results()` sont sur le `LLMClient` Protocol, pas dans les services. Chaque implémentation produit le format de messages correct pour sa conversation multi-turn.
**Context** : Anthropic et OpenAI ont des formats de messages tool_use incompatibles (content blocks vs function calling). Mettre la traduction dans les services (instanceof checks) est une abstraction qui fuit. La placer sur le client garde les services provider-agnostic.
**Alternatives** : isinstance checks dans CompanyAnalyzer (fait puis retiré — trop fragile), format de messages normalisé interne (over-engineering pour un seul consommateur).
**Date** : 2026-05-23

### Prompts dans le repo, vault comme override optionnel
**Decision** : les prompts vivent dans `app/prompts/*.py` (source de vérité). `PromptLoader` tente d'abord le vault (si `prompts` configuré dans vault_layout.yaml), sinon utilise les constantes Python. En pratique, la section `prompts` est commentée dans vault_layout.yaml → les constantes Python sont toujours utilisées.
**Context** : les prompts sont couplés au code (schémas JSON, format attendu, system instructions). Avoir la source de vérité dans le vault créait un risque de drift (deux repos à synchroniser). Le vault reste disponible pour expérimenter sans toucher au code.
**Alternatives** : vault-first (implémenté puis revert — risque de drift), tout dans le vault sans fallback (fragile), pas de PromptLoader du tout (perd l'injection par constructeur utile pour les tests).
**Date** : 2026-05-24

### Prompts injectés par constructeur, pas importés
**Decision** : les services (OfferAnalyzer, CompanyAnalyzer, CoverLetterGenerator, OutreachGenerator) reçoivent leur prompt en paramètre `prompt: str` via le constructeur. Le pipeline charge les prompts via `PromptLoader` et les passe.
**Context** : l'import direct (`from app.prompts import X`) couplait les services à un module spécifique. L'injection permet de tester avec des prompts arbitraires et d'activer l'override vault sans modifier les services.
**Alternatives** : import direct (ancien comportement — couplage fort), prompt sur le Protocol LLMClient (surcharge le client avec du contenu métier).
**Date** : 2026-05-24

### Outreach en parallèle avec la lettre, pas dans le même appel LLM
**Decision** : `OutreachGenerator` est un service séparé de `CoverLetterGenerator`. Les deux sont lancés en `asyncio.gather` dans le pipeline. Ils produisent des artefacts distincts mais sont combinés dans le même fichier `.lettre.md`.
**Context** : un seul appel produisant lettre + outreach serait plus efficient mais rendrait le prompt trop complexe et empêcherait d'utiliser des températures différentes (0.7 pour la lettre, 0.5 pour l'outreach). La parallélisation compense le surcoût de deux appels.
**Alternatives** : un seul appel LLM (prompt trop gros, une seule température), outreach dans un fichier séparé (l'utilisateur préfère tout dans le même document).
**Date** : 2026-05-24

### Abandon du few-shot dynamique
**Decision** : la direction "few-shot depuis les candidatures validées (status: applied)" est abandonnée.
**Context** : le prompt rewritten avec directives de ton issues de Personnalite.md + 1 exemple (Beta.gouv DIALOG) couvre le besoin d'alignement stylistique. Le few-shot dynamique ajoutait de la complexité (scan du vault, sélection des meilleurs exemples, injection conditionnelle) pour un gain incertain. Les ancres narratives dans le prompt servent de substitut.
**Alternatives** : implémenter le few-shot (complexité non justifiée à ce stade).
**Date** : 2026-05-24

### Config unique `config.yaml` — vault + LLM + serveur
**Decision** : toute la config métier (vault, modèles LLM, températures, seuils, serveur) vit dans un seul `config.yaml` à la racine. `.env` ne contient que les secrets (API keys, AUTH_TOKEN).
**Context** : la config était split entre `vault_layout.yaml` (vault) et `.env` (modèles, températures, seuils). C'était incohérent — un fichier YAML structuré et un fichier KEY=VALUE mélangés. L'homogénéisation simplifie la mental model : un fichier pour la config métier versionnable, un fichier pour les secrets sensibles.
**Alternatives** : garder le split (status quo — fragmentation), tout mettre dans `.env` (pas structuré pour du nesting), YAML par domaine (`vault_layout.yaml` + `llm_config.yaml` — plus de fichiers).
**Date** : 2026-05-26

### Pipeline accepte `app_config` optionnel
**Decision** : `Pipeline.__init__` reçoit `settings: Settings` (secrets) et `app_config: AppConfig | None = None`. Si `app_config` est absent, il appelle `get_app_config()`.
**Context** : le mode CLI permet d'override la température via `--temperature`. Avec `get_app_config()` en `lru_cache`, modifier la config globale polluerait tous les appels futurs. Passer une copie locale (`model_copy(deep=True)`) au `Pipeline` isole l'override.
**Alternatives** : monkeypatch `get_app_config()` en CLI (fragile, affecte le cache), ne pas supporter `--temperature` en CLI (régression UX).
**Date** : 2026-05-26
