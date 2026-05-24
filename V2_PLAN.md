# Job Set & Match — V2 Plan d'action

## Vision

Outil personnel de veille emploi, frictionless :
- **Input** : clic depuis Firefox sur une offre (même authentifiée)
- **Processing** : analyse Claude (offre + entreprise + profil perso)
- **Output** : dossier structuré écrit directement dans le vault Obsidian
- **Dashboard** : Obsidian Bases (pas de UI custom)

---

## Architecture cible

```
Firefox plugin (page authentifiée)
    → POST { url, title, content } → app locale (FastAPI)
         ↓
    Screenshot MCP  → capture.pdf
    Fetch MCP       → texte propre (si URL publique, fallback)
         ↓
    Claude API (tool_use) :
      • ANALYSIS_PROMPT × documents perso (lus depuis Obsidian)
      • COMPANY_PROMPT  × Brave Search MCP (recherche auto entreprise)
         ↓
    Score gate (chanceRating < seuil → archivé, fin)
         ↓
    GENERATION_PROMPT → lettre.md
         ↓
    Écriture directe vault Obsidian :
      /Job Search/Offers/{Company}/{YYYY-MM-DD}_{position}/
        ├── analyse.md       ← frontmatter Bases + contenu
        ├── entreprise.md
        ├── lettre.md
        └── capture.pdf
         ↓
    Obsidian Bases → dashboard / CRM
```

---

## Stack technique

| Composant | Choix | Raison |
|-----------|-------|--------|
| Backend | FastAPI | Léger, endpoint POST propre, async natif |
| AI | Anthropic SDK (tool_use) | MCPs comme outils Claude |
| Fetch contenu | Fetch MCP (Anthropic officiel) | HTML → Markdown propre |
| Capture page | Screenshot MCP (Seth Bang) ou Playwright | PDF/PNG archival |
| Recherche entreprise | Brave Search MCP | Free tier, pas Google |
| Vault output | Écriture fichiers directe (pathlib) | Vault = dossier sur disque, pas besoin de plugin |
| UI | Streamlit minimal OU supprimé | Juste un affichage de statut si besoin |
| Python | 3.11+ | Meilleure perf async vs 3.9 |

---

## Documents personnels (Obsidian → App)

Lus depuis le vault au moment de l'analyse. Chemin configurable.

| Fichier | Contenu | Utilisé dans |
|---------|---------|-------------|
| `bio.md` | Mini bio narrative | ANALYSIS_PROMPT + GENERATION_PROMPT |
| `experiences_star.md` | Expériences format STAR | GENERATION_PROMPT |
| `competences.md` | Stack technique, soft skills | ANALYSIS_PROMPT |
| `personnalite.md` | Tests de personnalité, style | GENERATION_PROMPT (ton) |

Optionnel : pré-traitement via CONTEXT_PROMPT pour générer un profil consolidé
avant chaque analyse (coût supplémentaire, mais input plus riche).

---

## Frontmatter Obsidian (pour Bases)

Chaque `analyse.md` commence par :

```yaml
---
company: "Acme Corp"
position: "Data Engineer"
date: 2026-04-08
url: "https://..."
score_career: 7.5
score_match: 8.0
score_success: 6.5
score_chance: 7.0
score_total: 29.0
decision: true
status: "pending"   # pending | applied | interview | rejected | offer
location: "Paris"
---
```

Obsidian Bases peut alors filtrer/trier/kanban sur ces champs.

---

## Plugin Firefox

### Manifest V3 — structure minimale

```
firefox-plugin/
  ├── manifest.json
  ├── popup/
  │   ├── popup.html
  │   └── popup.js
  ├── content/
  │   └── extract.js    ← extrait title + url + body text
  └── background/
      └── service_worker.js  ← POST vers localhost
```

### Comportement

1. Clic sur l'icône plugin → popup "Analyser cette offre"
2. `extract.js` capture `document.title`, `location.href`, `document.body.innerText`
3. POST `http://localhost:8000/analyze` avec le payload
4. Feedback visuel : spinner → "Analysé ✓" ou "Erreur"

### Sécurité

- L'endpoint FastAPI n'écoute que sur `127.0.0.1` (pas `0.0.0.0`)
- CORS restreint à l'extension Firefox uniquement
- **Auth token** : header `X-Auth-Token` partagé entre extension (`storage.local`) et FastAPI (`.env`). Le CORS seul ne protège pas le serveur (appliqué par le navigateur, pas par le serveur — curl/scripts locaux passent au travers).
- **Path traversal** : slugifier company/position avant construction du chemin + vérifier que `Path.resolve()` reste sous `OBSIDIAN_VAULT_PATH`
- **Clé API** : `.env` dans `.gitignore`, jamais exposée côté extension

---

## Phases de développement

### Phase 0 — Setup projet (1 session)
- [ ] Nouveau dossier projet `app-jobset-match-v2/`
- [ ] `pyproject.toml` (uv ou poetry), Python 3.11
- [ ] Structure : `app/`, `plugin/`, `config/`, `_archive/`
- [ ] Copier `_prompts_archive/prompts_v2.py` → `app/prompts/`
- [ ] `.env.example` documenté
- [ ] Config : `OBSIDIAN_VAULT_PATH`, `OBSIDIAN_PERSONAL_DOCS_PATH`, `ANTHROPIC_API_KEY`, `BRAVE_API_KEY`, `SCORE_THRESHOLD`, `AUTH_TOKEN`
- [ ] `.gitignore` avec `.env`, `*.log`
- [ ] Logging basique (`logging.basicConfig` vers fichier `jobsetmatch.log`)

### Phase 1 — Plugin Firefox (1-2 sessions)
- [ ] `manifest.json` Manifest V3
- [ ] `extract.js` : extraction title + url + body text
- [ ] `popup.html/js` : bouton + feedback
- [ ] `service_worker.js` : POST vers FastAPI avec header `X-Auth-Token`
- [ ] Garde-fou contenu : tronquer si > 15000 chars, flag si < 200 chars (fallback Fetch MCP côté serveur)
- [ ] Test sur WTTJ, LinkedIn, APEC, Indeed FR
- [ ] ⚠️ Manifest V3 Firefox encore en évolution — tester `activeTab` + `scripting` sur pages auth LinkedIn (CSP restrictive). Fallback : `tabs.executeScript` depuis le background script

### Phase 2 — Backend core (2-3 sessions)
- [ ] FastAPI app avec endpoint `POST /analyze`
- [ ] Middleware auth : vérifier `X-Auth-Token` sur chaque requête
- [ ] Déduplication : ignorer les requêtes sur la même URL dans une fenêtre de 30s
- [ ] Semaphore : limiter à 1 analyse simultanée (usage mono-utilisateur)
- [ ] `DocumentLoader` : lit les docs perso depuis le vault Obsidian
- [ ] `OfferAnalyzer` : ANALYSIS_PROMPT × docs perso → JSON
- [ ] Score gate configurable (`SCORE_THRESHOLD`) — **démarrer sans seuil bloquant**, tout archiver, calibrer après 15-20 analyses
- [ ] `ObsidianWriter` : crée le dossier + écrit les fichiers
  - Slugifier company/position pour les noms de dossiers
  - Vérifier `Path.resolve()` sous `OBSIDIAN_VAULT_PATH`
  - Détecter si le dossier existe déjà (warning + suffixe `_v2`)
- [ ] Logger `usage` tokens de chaque appel Anthropic (suivi coûts)
- [ ] Mode CLI : `if __name__ == "__main__"` pour tester sans le plugin

### Phase 3 — MCPs (1-2 sessions)
- [ ] Intégrer Fetch MCP (fallback si contenu extension < 200 chars)
- [ ] Intégrer Playwright `page.pdf()` → `capture.pdf` (page complète, couche texte cherchable)
- [ ] Intégrer Brave Search MCP comme tool Claude → `CompanyAnalyzer`
- [ ] Activer COMPANY_PROMPT → `entreprise.md`
- [ ] Timeouts explicites : 10-15s Fetch, 20-30s Screenshot, 10s Brave Search
- [ ] Fallback gracieux : si un MCP échoue, continuer l'analyse sans (ne pas bloquer le pipeline)

### Phase 4 — Lettre de motivation (1 session)
- [ ] `CoverLetterGenerator` : GENERATION_PROMPT × analyse × docs perso
- [ ] Déclenché si `decision == true`
- [ ] Output : `lettre.md` dans le dossier Obsidian

### Phase 5 — Obsidian Bases (1 session)
- [ ] Créer la vue Bases dans le vault
- [ ] Configurer colonnes : company, position, date, scores, status
- [ ] Créer vue Kanban sur `status`
- [ ] Tester le pipeline end-to-end

---

## Questions ouvertes / décisions différées

1. ~~**FastAPI vs script CLI**~~ → **FastAPI** (justifié par le plugin Firefox) + mode CLI à côté pour debug.
2. ~~**CONTEXT_PROMPT**~~ → **Skip pour le MVP**. Injecter les docs bruts directement dans les prompts. Surcoût tokens négligeable vs appel API supplémentaire. Revisiter si docs perso > 5000 tokens.
3. ~~**Score threshold**~~ → **Pas de seuil bloquant au départ**. Tout archiver, calibrer après 15-20 analyses sur la distribution réelle des scores.
4. ~~**Screenshot MCP : PNG ou PDF ?**~~ → **PDF via Playwright `page.pdf()`**. Les annonces sont souvent longues (multi-pages) : le PDF gère nativement le scroll complet en un seul fichier, avec couche texte cherchable. PNG nécessiterait du découpage multi-fichiers.
5. ~~**Automa**~~ → **Plugin Firefox custom** (~50 lignes de JS). Automa est une dépendance lourde et fragile pour un besoin simple.

---

## Ce qu'on réutilise de V1

| Élément | Statut |
|---------|--------|
| `ANALYSIS_PROMPT` | Copié tel quel |
| `COMPANY_PROMPT` | Copié, à activer |
| `CONTEXT_PROMPT` | Copié, à utiliser pour docs perso |
| `GENERATION_PROMPT` | Copié tel quel (4 exemples réels) |
| Logique score gate (`shouldApply.decision`) | Réutilisée |
| `generate_analysis_markdown()` | Réutilisée / adaptée |

## Ce qu'on ne réutilise pas

- `file_manager.py` (pipeline PDF → remplacé par plugin + Fetch MCP)
- `data_handler.py` (JSON/Parquet → remplacé par vault Obsidian)
- Gestion PDF upload Streamlit
- `analyze_pdfs_parallel()` (async mal implémenté)
