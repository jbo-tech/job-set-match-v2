# Phase 5 — Restructuration vault + Bases + Test E2E

Ce guide couvre trois choses :
1. **Restructuration de ton vault existant** pour qu'il colle aux contrats du backend
2. **Setup Obsidian Bases + Kanban** pour dashboarder les offres
3. **Checklist E2E** pour valider plugin et CLI en parallèle

---

## 1. Structure vault attendue par le backend

### 1.1 Arborescence de référence

Le backend écrit et lit à ces emplacements précis :

```
<OBSIDIAN_VAULT_PATH>/
├── Job Search/
│   ├── Offers/                       ← écriture par ObsidianWriter
│   │   └── {company-slug}/
│   │       └── {YYYY-MM-DD}_{position-slug}/
│   │           ├── analyse.md        (toujours — frontmatter YAML + corps)
│   │           ├── entreprise.md     (optionnel — CompanyAnalyzer + Brave)
│   │           ├── lettre.md         (optionnel — si decision=true)
│   │           └── capture.pdf       (optionnel — Playwright)
│   ├── Dashboard.base                ← à créer (vue Bases tabulaire)
│   └── Kanban.base                   ← à créer (vue Kanban sur `status`)
```

Et les docs perso (injectés dans chaque prompt Claude) :

```
<OBSIDIAN_PERSONAL_DOCS_PATH>/
├── bio.md              ← Qui tu es, ton parcours en prose
├── experiences_star.md ← Expériences au format STAR (Situation/Task/Action/Result)
├── competences.md      ← Compétences techniques + soft skills
└── personnalite.md     ← Traits de personnalité, valeurs, mode de travail
```

**Important** :
- Les 4 docs perso sont obligatoires (warning si manquants, prompt dégradé).
- `OBSIDIAN_PERSONAL_DOCS_PATH` peut être **à l'intérieur** de `OBSIDIAN_VAULT_PATH` (ex : `{vault}/Personal/profile/`) ou complètement à l'extérieur. Le backend ne s'en mêle pas.

### 1.2 Vérifier ton `.env`

```bash
# Dans .env (à la racine du projet)
OBSIDIAN_VAULT_PATH=/home/jbo/Documents/Obsidian/MonVault
OBSIDIAN_PERSONAL_DOCS_PATH=/home/jbo/Documents/Obsidian/MonVault/Personal/profile
ANTHROPIC_API_KEY=sk-ant-...
BRAVE_API_KEY=BSA...
AUTH_TOKEN=un-token-long-et-random  # utilisé par plugin + backend
```

Astuce token : `openssl rand -hex 32` pour générer un token solide.

---

## 2. Migration du vault existant

### 2.1 Audit de l'existant

Lance d'abord un petit audit pour voir ce qui existe :

```bash
# Remplace par le chemin de ton vault
VAULT=/home/jbo/Documents/Obsidian/MonVault

# Y a-t-il déjà un dossier d'offres quelque part ?
find "$VAULT" -type d -iname "*job*" -o -iname "*offre*" -o -iname "*candid*" 2>/dev/null

# Docs perso déjà présents ?
find "$VAULT" -type f \( -name "bio*.md" -o -name "experien*.md" -o -name "competen*.md" -o -name "personnal*.md" \)
```

### 2.2 Stratégie de migration

Trois cas possibles :

#### Cas A — Vault vierge côté job search
Rien à migrer. Crée juste les dossiers et les docs perso :

```bash
mkdir -p "$VAULT/Job Search/Offers"
mkdir -p "$VAULT/Personal/profile"
# Puis édite bio.md, experiences_star.md, competences.md, personnalite.md
```

#### Cas B — Offres V1 avec une structure différente
Tu as peut-être des dossiers type `Candidatures/Acme/2024-05-12 Data Engineer/` ou similaire.

**Recommandation** : ne migre pas rétroactivement. Archive l'ancien dans `Job Search/Archive V1/` et laisse V2 remplir à neuf. Raison : l'ancien format n'a pas le frontmatter YAML attendu par Bases, et les scores/decision n'existent pas.

```bash
mkdir -p "$VAULT/Job Search"
# Si l'ancien dossier s'appelait "Candidatures" :
mv "$VAULT/Candidatures" "$VAULT/Job Search/Archive V1"
mkdir "$VAULT/Job Search/Offers"
```

Les anciennes offres restent lisibles et indexables par Obsidian, simplement hors du périmètre Bases V2.

#### Cas C — Docs perso existants mais mal nommés
Si tu as déjà `CV.md`, `Profil.md`, etc., **renomme-les** plutôt que de dupliquer. Le `DocumentLoader` attend ces 4 noms exacts : `bio.md`, `experiences_star.md`, `competences.md`, `personnalite.md` (voir `app/services/document_loader.py:14`).

### 2.3 Contenu minimal des docs perso

Si tu pars de zéro, voici les squelettes minimaux.

**`bio.md`** — prose fluide (500-1500 mots)
```markdown
# Bio

Je suis Jean-Baptiste Odin, 10+ ans en pilotage de projets digitaux...
[parcours chronologique, reconversion, moment pivot, vision actuelle]
```

**`experiences_star.md`** — une expérience par section, format STAR
```markdown
# Expériences (STAR)

## Refonte produits-laitiers.com — CNIEL (2020-2023)

**Situation** : écosystème digital de 20+ sites, 1M visiteurs/an, silos techniques.
**Task** : rationaliser, introduire le data-driven, former les équipes.
**Action** : mise en place tableaux de bord Looker, refonte centrée utilisateur, co-construction no-code.
**Result** : +40% temps passé sur site, adoption méthodo par 3 pôles, budget divisé par 2.

## [Expérience suivante]
...
```

**`competences.md`** — technique + soft skills
```markdown
# Compétences

## Techniques
- **Data** : Python, SQL, pandas, scikit-learn, PyTorch (bootcamp Le Wagon)
- **Cloud** : Docker, GCP (BigQuery, Cloud Run), basic Kubernetes
- ...

## Soft skills
- Pilotage d'équipe pluridisciplinaire (13 personnes)
- Facilitation d'ateliers
- ...
```

**`personnalite.md`** — valeurs, mode de travail
```markdown
# Personnalité

## Valeurs
- Autonomie et responsabilisation
- Approche pragmatique, pas de sur-ingénierie
- ...

## Mode de travail
- Écrit > réunion
- ...
```

Ces 4 fichiers alimentent le `cache_control: ephemeral` de Claude → ils sont cachés entre l'appel analyse et l'appel lettre, donc pas de coût double.

---

## 3. Setup Obsidian Bases (plugin core)

Bases est un core plugin Obsidian (depuis 1.8). Vérifie qu'il est activé : **Paramètres → Plugins de base → Bases → Activer**.

### 3.1 Base principale : Dashboard des offres

Crée un fichier `Job Search/Dashboard.base` à la racine du dossier `Job Search/`.

**Contenu YAML** :

```yaml
filters:
  and:
    - file.path.startsWith("Job Search/Offers/")
    - file.name == "analyse"

properties:
  company:
    displayName: Entreprise
  position:
    displayName: Poste
  date:
    displayName: Date
  location:
    displayName: Lieu
  score_total:
    displayName: Score /40
  score_chance:
    displayName: Chance /10
  decision:
    displayName: Go
  status:
    displayName: Statut
  url:
    displayName: URL

views:
  - type: table
    name: Toutes les offres
    order:
      - date
      - company
      - position
      - location
      - score_total
      - score_chance
      - decision
      - status
    sort:
      - property: date
        direction: DESC

  - type: table
    name: À postuler (filtrées)
    filters:
      and:
        - decision == true
        - status == "pending"
    order:
      - score_total
      - company
      - position
      - score_chance
    sort:
      - property: score_total
        direction: DESC

  - type: table
    name: Score minimum 25/40
    filters:
      and:
        - score_total >= 25
    sort:
      - property: score_total
        direction: DESC
```

**Note sur le filtre `file.name == "analyse"`** : c'est nécessaire car chaque dossier d'offre contient aussi `entreprise.md` et `lettre.md` qui n'ont pas le même frontmatter. On ne veut voir qu'`analyse.md` dans la base.

### 3.2 Vue Kanban sur le statut

Deux options :

#### Option A — Bases natif (recommandé)
Ajoute une view `cards` à la même base :

```yaml
  - type: cards
    name: Pipeline (Kanban)
    groupBy: status
    order:
      - company
      - position
      - score_total
```

Obsidian Bases ne fait pas encore de vrai Kanban drag-and-drop comme le plugin communautaire, mais le `groupBy: status` donne des colonnes lisibles.

#### Option B — Plugin Kanban communautaire
Si tu veux le drag-and-drop : installe le plugin communautaire **Kanban** (mgmeyers), crée un fichier `Job Search/Pipeline.md` type Kanban. Tu devras linker manuellement les offres vers les cartes — moins automatique mais plus ergonomique.

**Recommandation** : commence avec l'option A (natif, zéro config supplémentaire). Si ça te frustre au bout d'une semaine, passe en B.

### 3.3 Valeurs de `status`

Le backend écrit `status: pending` par défaut (voir `app/services/obsidian_writer.py:108`). Toi, tu éditeras manuellement les frontmatter quand une candidature avance. Valeurs conventionnelles :

| Valeur      | Sens                                    |
|-------------|-----------------------------------------|
| `pending`   | Analysée, pas encore envoyée (défaut)   |
| `applied`   | Candidature envoyée                     |
| `interview` | Entretien décroché                      |
| `offer`     | Offre reçue                             |
| `rejected`  | Refusée (par toi ou par eux)            |
| `ghosted`   | Pas de réponse après X semaines         |

Tu peux ajouter une vue filtrée par statut si tu veux suivre chaque étape :

```yaml
  - type: table
    name: En entretien
    filters:
      and:
        - status == "interview"
    sort:
      - property: date
        direction: DESC
```

---

## 4. Checklist Test E2E

### 4.1 Pré-requis avant tout test

```bash
cd /home/jbo/Wip/coding/projects-python/app-jobset\&match-v2

# 1. Sync deps
uv sync --extra dev

# 2. Playwright chromium (pour la capture PDF — ~170 MB)
uv run playwright install chromium

# 3. .env bien rempli (cf. section 1.2)
cat .env

# 4. Les 4 docs perso existent et ont du contenu
ls -la "$OBSIDIAN_PERSONAL_DOCS_PATH"

# 5. Tests unitaires au vert (sanity check)
uv run pytest
# → 42 passed
```

### 4.2 Test CLI — le plus rapide

Le mode CLI court-circuite le plugin et le serveur. Utile pour valider toute la chaîne backend avec du contenu local.

```bash
# Récupère du contenu d'offre dans un fichier
cat > /tmp/offre_test.txt <<'EOF'
Data Scientist H/F — Acme SAS

Acme, éditeur logiciel B2B, recrute un Data Scientist...
[colle ici 500-2000 mots d'une vraie offre]
EOF

# Lance le pipeline complet
uv run python -m app.main "https://example.com/offre/datascientist-acme" /tmp/offre_test.txt
```

**Ce que tu dois voir** :
1. Logs : "Analyse démarrée", "Documents perso chargés : 4/4", appels Claude, "Décision : True/False"
2. JSON en sortie : `{"status": "success", "company": "...", "vault_path": "..."}`
3. Dans le vault : `Job Search/Offers/acme-sas/2026-04-11_data-scientist/analyse.md`
4. `entreprise.md` présent si Brave a répondu
5. `lettre.md` présent si `decision == true`
6. `capture.pdf` : **non** (le CLI passe une URL fictive, Playwright échouera proprement → None, OK)

**Variantes à tester** :
```bash
# Test avec stdin
cat /tmp/offre_test.txt | uv run python -m app.main "https://example.com/job/1"

# Test avec une URL publique réelle (testera la capture PDF)
cat /tmp/offre_test.txt | uv run python -m app.main "https://www.welcometothejungle.com/fr/companies/acme/jobs/data-scientist_paris"
```

### 4.3 Test serveur HTTP — curl

Démarre le serveur dans un terminal :

```bash
uv run uvicorn app.main:app --reload
```

Dans un autre terminal :

```bash
# Health check (pas d'auth)
curl http://127.0.0.1:8000/health
# → {"status":"ok"}

# Analyse (avec token)
AUTH=$(grep ^AUTH_TOKEN .env | cut -d= -f2)
curl -X POST http://127.0.0.1:8000/analyze \
  -H "Content-Type: application/json" \
  -H "X-Auth-Token: $AUTH" \
  -d @- <<'EOF'
{
  "url": "https://example.com/offre/test",
  "title": "Data Scientist — Acme",
  "content": "[colle 500+ chars de contenu réel]",
  "needs_fetch": false
}
EOF

# Test sans token → doit renvoyer 401
curl -X POST http://127.0.0.1:8000/analyze \
  -H "Content-Type: application/json" \
  -d '{"url":"https://x","title":"x","content":"x"}'
# → 401 Unauthorized

# Test déduplication (rejoue la même URL dans les 30s)
# → {"status":"deduplicated"}
```

### 4.4 Test plugin Firefox

Dans Firefox :

1. **Charger l'extension** : `about:debugging` → "Ce Firefox" → "Charger un module complémentaire temporaire" → sélectionne `plugin/manifest.json`
2. **Configurer le token** : clique sur l'icône de l'extension → ouvre `Paramètres` → colle le `AUTH_TOKEN` → `Enregistrer`
3. **Tester** : navigue sur une offre → clique l'icône → `Analyser cette offre`

**Sites à tester par ordre de difficulté** :

| Site | Attendu | Notes |
|------|---------|-------|
| Welcome to the Jungle | ✅ Extract OK, PDF OK | Site le plus propre, CSP permissive |
| APEC | ✅ Extract OK | Souvent 2-3 écrans de contenu |
| Indeed FR | ⚠️ Extract OK, PDF peut-être login wall | L'extraction plugin marche, le PDF Playwright verra la page publique |
| LinkedIn Jobs | ⚠️ CSP stricte — si l'extraction plugin rate, le backend tentera `fetch_clean_text` fallback | Le test ultime |

**Pour chaque site, vérifier** :
- [ ] Popup passe en `loading` puis `success`
- [ ] Dans le popup : entreprise + poste + décision + score affichés
- [ ] Dans `jobsetmatch.log` (à la racine du projet) : pas d'erreur rouge
- [ ] Dans le vault : dossier créé avec `analyse.md` + frontmatter YAML valide
- [ ] `entreprise.md` présent (sauf si `BRAVE_API_KEY` vide)
- [ ] `lettre.md` présent si decision=true
- [ ] `capture.pdf` présent (sauf LinkedIn avec login wall)
- [ ] Dans Obsidian : la nouvelle offre apparaît dans `Dashboard.base`
- [ ] Kanban : la nouvelle carte est bien dans la colonne `pending`

### 4.5 Diagnostic des problèmes fréquents

| Symptôme | Cause probable | Fix |
|----------|----------------|-----|
| Popup : "AUTH_TOKEN manquant" | Token pas sauvegardé dans `storage.local` | Ouvre les paramètres du popup, re-entre, Enregistre |
| Popup : "HTTP 401" | Token plugin ≠ token `.env` | Compare les 2, re-synchronise |
| Popup : "HTTP 422" | Pydantic validation fail | Regarde les logs backend — probablement `url` pas un HttpUrl valide |
| Popup : "Timeout (120s)" | Claude a pris plus de 2min (rare) | Vérifier logs, relancer |
| Logs : "Contenu plugin trop court" | Page avec beaucoup de JS, extract.js n'a rien trouvé | Le backend déclenche `fetch_clean_text` en fallback, souvent OK |
| Logs : "CompanyAnalyzer échec : BRAVE_API_KEY" | Clé absente | Renseigne `BRAVE_API_KEY` dans `.env`, redémarre uvicorn |
| Logs : "capture_pdf échec : net::ERR_" | URL privée / réseau | Normal, le PDF est best-effort |
| Logs : "Échec parsing JSON Claude" | Claude a répondu en markdown au lieu de JSON | Voir `offer_analyzer._extract_json` — il y a 3 fallbacks, si ça échoue quand même, inspecter la réponse dans les logs |
| Dashboard Bases : offre invisible | Filtre `file.name == "analyse"` pas matché | Vérifier que le fichier s'appelle bien `analyse.md` (pas `Analyse.md`) |
| Dashboard Bases : toutes les offres absentes | Plugin Bases désactivé ou chemin du filter faux | Paramètres → Plugins de base → Bases ; vérifier `file.path.startsWith("Job Search/Offers/")` correspond à l'arbo |
| Frontmatter YAML cassé dans analyse.md | Character spécial non échappé | Bug potentiel à remonter — envoyer l'exemple au dev |

### 4.6 Checklist finale Phase 5

- [ ] Vault restructuré : `Job Search/Offers/` vide, `Personal/profile/` rempli avec les 4 docs
- [ ] `.env` complet (vault path, docs path, API keys, AUTH_TOKEN)
- [ ] `uv sync --extra dev` OK
- [ ] `uv run playwright install chromium` OK
- [ ] `uv run pytest` → 42/42 passent
- [ ] CLI : test sur offre locale → dossier créé, `analyse.md` + `lettre.md` (si decision=true)
- [ ] Serveur HTTP : `curl /health` OK, `curl /analyze` avec token OK, sans token → 401
- [ ] Plugin Firefox : chargé via `about:debugging`, token configuré
- [ ] Plugin testé sur WTTJ → success
- [ ] Plugin testé sur APEC → success
- [ ] Plugin testé sur Indeed FR → success ou fallback gracieux
- [ ] Plugin testé sur LinkedIn → success ou fallback `fetch_clean_text`
- [ ] `Dashboard.base` créé → affiche les offres
- [ ] Vue Kanban fonctionnelle → les cartes apparaissent dans la bonne colonne
- [ ] Édition manuelle `status: applied` → carte bouge bien de colonne après refresh

---

## 5. Ce qui reste après Phase 5

Une fois tout ça validé, la V2 est **utilisable en prod perso**. Les améliorations futures possibles (hors scope actuel) :

- Icônes du plugin (PNG 16/48/128)
- Retry automatique si Claude renvoie du JSON cassé
- Mode batch (analyser plusieurs URLs d'un coup)
- Historique des coûts (`token_logger` persiste déjà en mémoire, mais pas sur disque)
- Export CSV des offres depuis Bases pour stats mensuelles
- Notifs système (desktop) à la fin de l'analyse

---

## Annexe : comment relancer une analyse identique

Le dédup bloque les re-runs dans les 30 secondes. Si tu veux forcer une re-analyse :

**Option 1** : attends 30s, relance.
**Option 2** : redémarre uvicorn (le cache dédup est en mémoire, vidé au redémarrage).
**Option 3** : pour le CLI, aucun dédup appliqué → relance à volonté.

Si tu veux supprimer une offre créée pendant les tests :

```bash
rm -rf "$VAULT/Job Search/Offers/acme-sas/2026-04-11_data-scientist"
```

Le dossier parent `acme-sas/` reste (tant qu'il n'est pas vide, ou tu le vires aussi). Aucun impact sur la base de données Obsidian — Bases re-scannera.
