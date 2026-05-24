# APP_INTEGRATION_SPEC

Contrat d'intégration entre le vault `/home/jbo/Obsidian/career/` et l'app `jobset&match-v2`.

**Date** : 2026-04-22
**Statut** : à appliquer côté app avant prochain test E2E
**Pendant** : `PHASE_5_GUIDE.md` (perspective app → vault). Ce document est la perspective vault → app.

---

## 1. Principes directeurs

1. **Le vault est la source de vérité de l'organisation.** L'app s'y plie.
2. **Une seule source de vérité par fichier.** Pas de duplication app↔vault.
3. **Anti-duplication systémique.** Si une donnée existe (entité, offre extraite), on ne la régénère pas.
4. **Annotations manuelles inviolables.** Un refresh ne doit jamais écraser ce que l'utilisateur a écrit à la main.
5. **Numérotation `01_…06_` conservée.** C'est un workflow méthodologique, pas des catégories d'objets.

---

## 2. Arborescence cible du vault

```
/home/jbo/Obsidian/career/
├── 01_Profilage/                              ← docs perso (5 fichiers, mapping configurable)
│   ├── Jean-Baptiste - Mon CV.md
│   ├── Jean-Baptiste - Mes expériences.md
│   ├── Jean-Baptiste - Mon Pitch.md
│   ├── Jean-Baptiste - Profil Professionnel Actualisé 2025.md
│   └── Jean-Baptiste - Questions cles.md
│
├── 02_Companies/                              ← référentiel d'entités du marché
│   ├── Acme.md                                ← écrit par l'app si absent, sinon skip
│   ├── OCTO.md
│   └── … (avec bloc `## Contacts` éventuel, écrit à la main)
│
├── 04_Applications/                           ← offres en cours (4 artefacts plats par offre)
│   ├── Acme - Data Scientist - 2026-04-22.offre.md
│   ├── Acme - Data Scientist - 2026-04-22.analyse.md
│   ├── Acme - Data Scientist - 2026-04-22.lettre.md
│   ├── Acme - Data Scientist - 2026-04-22.pdf
│   └── _Archive_V1/                           ← legacy, intouchable par l'app
│
├── 05_Daily/                                  ← inchangé, hors scope app
├── 06_Resources/                              ← inchangé, hors scope app
│
├── PHASE_5_GUIDE.md                           ← guide app (perspective backend)
├── APP_INTEGRATION_SPEC.md                    ← ce fichier
└── MIGRATION_PLAN.md                          ← plan de migration vault
```

**Notes** :
- `03_Network/` est supprimé. Les contacts existants sont migrés en bloc `## Contacts` dans la fiche entité concernée.
- `04_Applications/db/` disparaît : artefacts à plat directement dans `04_Applications/`.

---

## 3. Convention de slug

**Format** : `{Entreprise} - {Poste} - {YYYY-MM-DD}`

**Règles de slugification** :
- Préserver les espaces, accents, parenthèses (Obsidian les gère bien)
- Remplacer `/` → `_`, `:` → `-`, `\` → `_`, `|` → `-`, `*` → `_`, `?` → ``, `<>` → ``, `"` → `'`
- Tronquer chaque segment à 80 caractères max
- Date au format ISO court : `2026-04-22`

**Exemple** : `THIGA - Data Product Manager - 2026-04-22`

**Collision** : si deux offres ont le même slug le même jour (rare), suffixer `_2`, `_3`, etc.

---

## 4. Structure offre — 4 artefacts plats à préfixe commun

Pour une offre de slug `{slug}` :

| Fichier | Type | Contenu | Écrit par |
|---|---|---|---|
| `{slug}.offre.md` | brut | texte de l'offre extraite + frontmatter d'extraction | app, une fois (cache anti-redondance) |
| `{slug}.analyse.md` | analyse Claude | scoring, décision, raisonnement + zone d'annotation manuelle | app, écrasable si refresh manuel via versions `.analyse.v2.md` |
| `{slug}.lettre.md` | lettre Claude | lettre de motivation générée | app, overwrite à chaque génération |
| `{slug}.pdf` | binaire | capture Playwright filet de sécurité | app, best-effort |

### 4.1. `{slug}.offre.md`

**Frontmatter** :
```yaml
---
type: offre
slug: "Acme - Data Scientist - 2026-04-22"
url: https://www.welcometothejungle.com/fr/companies/acme/jobs/data-scientist
source: welcometothejungle.com
extracted_at: 2026-04-22
entreprise: "[[02_Companies/Acme]]"
poste: Data Scientist
localisation: Paris
contrat: CDI
salaire: null
---
```

**Corps** :
```markdown
# [Acme] Data Scientist

[[02_Companies/Acme]] — Paris — CDI

[Texte brut de l'offre, tel qu'extrait — sert de support de consultation principal]
```

**Cache anti-redondance** : si un `*.offre.md` contient déjà cette `url` dans son frontmatter, l'app skip toute la chaîne sauf si flag `--refresh`.

### 4.2. `{slug}.analyse.md`

**Frontmatter** :
```yaml
---
type: analyse
slug: "Acme - Data Scientist - 2026-04-22"
entreprise: "[[02_Companies/Acme]]"
poste: Data Scientist
analyzed_at: 2026-04-22
status: pending
score_total: 32       # /40
score_chance: 7       # /10
score_interet: 8.5    # /10 — intérêt pour la carrière
score_adequation: 7.8 # /10 — adéquation profil
score_succes: 7.0     # /10 — probabilité de succès
decision: true
---
```

**Corps** :
```markdown
# Analyse — Data Scientist @ [[02_Companies/Acme]]

## Résumé de l'offre
[…]

## Intérêt pour la carrière
**Note** : 8.5
- […]

## Adéquation du profil
**Note** : 7.8
- […]

## Probabilité de succès
**Note** : 7.0
- […]

## Décision
**Score total** : 32/40 — **GO**

## Sources
- [Lien vers l'offre]([[Acme - Data Scientist - 2026-04-22.offre.md]])

<!-- ZONE LIBRE — annotations manuelles ci-dessous, jamais touchée par l'app -->
```

### 4.3. `{slug}.lettre.md`

**Frontmatter** :
```yaml
---
type: lettre
slug: "Acme - Data Scientist - 2026-04-22"
entreprise: "[[02_Companies/Acme]]"
poste: Data Scientist
generated_at: 2026-04-22
lettre_status: draft   # draft | sent
sent_at: null
---
```

**Corps** :
```markdown
# Lettre — Data Scientist @ [[02_Companies/Acme]]

[Corps de la lettre, copiable d'un seul coup avec Ctrl+A]
```

**Re-génération** : overwrite atomique du fichier complet (l'utilisateur reformule à la main après — pas de versioning lettre, l'utilisateur sait qu'une re-génération réécrit).

### 4.4. `{slug}.pdf`

Capture Playwright. Best-effort. Aucun frontmatter possible (binaire). Si capture échoue, l'app log un warning et continue.

### 4.5. Refresh analyse → versions `.analyse.v2.md`

Si l'utilisateur déclenche un refresh d'analyse sur une offre déjà analysée :
- L'app **n'écrase pas** `{slug}.analyse.md`
- L'app crée `{slug}.analyse.v2.md` (puis `v3`, `v4`…) avec la nouvelle analyse
- Charge à l'utilisateur de comparer / merger / supprimer la précédente

---

## 5. Structure entité — `02_Companies/{Entreprise}.md`

**Frontmatter** :
```yaml
---
type: entite
nom: Acme
url: https://acme.com
analyzed_at: 2026-04-22
secteur: Conseil IT
taille: "675 employés (2021)"
implantations: "France, Maroc, Suisse, Brésil, Australie"
maturite_data: 4    # /5
score_culture: 5    # /5
---
```

**Corps** : structure libre, l'app génère ce qu'elle sait, l'utilisateur enrichit. Recommandation de squelette (à adapter au prompt côté app) :

```markdown
# Acme

## I. Carte d'identité
[…]

## II. Analyse Tech & Data
[…]

## III. Culture & Impact
[…]

## IV. Dynamiques & Opportunités
[…]

## V. Sources
- […]

## Contacts
<!-- Bloc géré à la main par l'utilisateur, jamais touché par l'app -->
- [[Sabrina Pierre]] — Recruteuse RH (rencontrée APEC 2025-01)
- [[Lionel - Montash]] — Account
```

**Cache** : si `02_Companies/{Entreprise}.md` existe (lookup par nom slugifié), l'app skip totalement la régénération. Refresh = suppression manuelle du fichier puis nouvelle analyse.

---

## 6. Mapping docs perso (`01_Profilage/`)

L'app actuelle hardcode 4 noms (`bio.md`, `experiences_star.md`, `competences.md`, `personnalite.md`) dans `app/services/document_loader.py:14`.

**Modification attendue** : rendre configurable via fichier `vault_layout.yaml` à la racine de l'app (lu au démarrage).

### Schéma `vault_layout.yaml`

```yaml
vault_root: /home/jbo/Obsidian/career

paths:
  applications: 04_Applications
  companies: 02_Companies
  archive: 04_Applications/_Archive_V1

personal_docs:
  cv:
    path: 01_Profilage/Jean-Baptiste - Mon CV.md
    cache: true
  experiences:
    path: 01_Profilage/Jean-Baptiste - Mes expériences.md
    cache: true
  pitch:
    path: 01_Profilage/Jean-Baptiste - Mon Pitch.md
    cache: true
  profil:
    path: 01_Profilage/Jean-Baptiste - Profil Professionnel Actualisé 2025.md
    cache: true
  questions:
    path: 01_Profilage/Jean-Baptiste - Questions cles.md
    cache: false
```

**Conséquences** :
- Les prompts Claude doivent être mis à jour : `{bio}` `{experiences_star}` etc. → `{cv}` `{experiences}` `{pitch}` `{profil}` `{questions}`.
- `cache: true` = injection avec `cache_control: ephemeral` (Claude prompt cache).
- `cache: false` (questions clés) = renvoyé à chaque appel sans cache (varie peu mais pas critique).

---

## 7. Frontmatter — récap des champs

| Champ | Type | Présent dans | Valeurs |
|---|---|---|---|
| `type` | enum | tous | `offre`, `analyse`, `lettre`, `entite` |
| `slug` | string | offre, analyse, lettre | `{Entreprise} - {Poste} - {YYYY-MM-DD}` |
| `url` | URL | offre, entite | URL source |
| `entreprise` | wikilink | offre, analyse, lettre | `"[[02_Companies/{Entreprise}]]"` |
| `poste` | string | offre, analyse, lettre | intitulé du poste |
| `localisation` | string | offre | ville/région |
| `contrat` | string | offre | CDI, CDD, freelance, … |
| `salaire` | string\|null | offre | si mentionné |
| `extracted_at` | date | offre | ISO `YYYY-MM-DD` |
| `analyzed_at` | date | analyse, entite | ISO |
| `generated_at` | date | lettre | ISO |
| `sent_at` | date\|null | lettre | ISO ou null |
| `status` | enum | analyse | voir §8 |
| `lettre_status` | enum | lettre | `draft`, `sent` |
| `score_total` | int 0-40 | analyse | somme des scores |
| `score_chance` | float 0-10 | analyse | proba succès estimée |
| `score_interet` | float 0-10 | analyse | intérêt carrière |
| `score_adequation` | float 0-10 | analyse | adéquation profil |
| `score_succes` | float 0-10 | analyse | proba candidature retenue |
| `decision` | bool | analyse | go/no-go |
| `nom` | string | entite | nom canonique |
| `secteur`, `taille`, `implantations` | string | entite | facultatifs |
| `maturite_data` | int 0-5 | entite | facultatif |
| `score_culture` | int 0-5 | entite | facultatif |

---

## 8. Statuts unifiés (champ `status` sur `.analyse.md`)

| Valeur | Sens |
|---|---|
| `pending` | Analysée, candidature pas envoyée (défaut à l'écriture) |
| `applied` | Candidature envoyée |
| `interview` | Entretien décroché |
| `offer` | Offre reçue |
| `rejected` | Refusée (par toi ou par eux) |
| `ghosted` | Pas de réponse après 3 semaines |

L'app écrit `pending` à la création. L'utilisateur édite manuellement le statut au fil de l'avancement (Bases ou édition directe).

---

## 9. Liaison offre → entité

**Double écriture** par l'app, à chaque création :
1. **Frontmatter** : `entreprise: "[[02_Companies/{Entreprise}]]"` (machine-readable, exploité par Bases)
2. **H1 du corps** : `# [{Entreprise}] {Poste}` ou ligne juste sous le H1 contenant `[[02_Companies/{Entreprise}]]` (humain-friendly)

**Pas de typage** (`client_final` / `intermédiaire`) — référentiel volontairement minimal.

---

## 10. Règles de cache

| Cache | Clé | Comportement |
|---|---|---|
| Cache entité | `02_Companies/{Entreprise}.md` (slugifié) | Skip total si fichier existe. Refresh = suppression manuelle. |
| Cache offre | `url` dans frontmatter `*.offre.md` | Skip total chaîne si une offre matche cette URL. Override via flag CLI `--refresh`. |
| Cache docs perso | Claude `cache_control: ephemeral` | Géré par API Anthropic, automatique selon `cache: true` dans `vault_layout.yaml`. |

---

## 11. Modifications attendues côté app — checklist ordonnée

À appliquer dans le repo `/home/jbo/Wip/coding/projects-python/app-jobset&match-v2`.

### 11.1. Configuration externalisée
- [ ] Créer `vault_layout.yaml` à la racine du repo (template fourni en §6)
- [ ] Ajouter `pyyaml` aux deps si absent
- [ ] Charger le fichier au démarrage dans une `VaultConfig` Pydantic (validation des paths existants)
- [ ] Exposer `VaultConfig` via injection de dépendance (FastAPI Depends)

### 11.2. `app/services/document_loader.py`
- [ ] Supprimer les noms hardcodés (`bio.md` etc.)
- [ ] Lire la liste des docs perso depuis `VaultConfig.personal_docs`
- [ ] Renvoyer un dict `{var_name: contenu}` (pas une dataclass figée)
- [ ] Warning explicite si un fichier listé est absent

### 11.3. `app/services/obsidian_writer.py`
- [ ] Supprimer la logique `Job Search/Offers/{company-slug}/{date}_{position-slug}/` actuelle
- [ ] Implémenter la logique R2 enrichi : 4 artefacts à plat dans `04_Applications/`
- [ ] Slugification selon §3
- [ ] Cache offre par URL avant écriture (§10)
- [ ] Refresh analyse → `.analyse.v2.md`, `.v3.md`, … (§4.5)
- [ ] Frontmatter conformes à §7

### 11.4. `app/services/company_analyzer.py` (ou équivalent)
- [ ] Cache entité avant analyse Brave + Claude (§5, §10)
- [ ] Si fichier entité absent : générer + écrire dans `02_Companies/{Entreprise}.md`
- [ ] Si présent : skip, retourner le path pour le wikilink

### 11.5. Prompts Claude (où qu'ils soient)
- [ ] Renommer les variables : `{bio}` → `{cv}+{profil}`, `{experiences_star}` → `{experiences}`, `{competences}` → `{cv}`, `{personnalite}` → `{pitch}+{profil}`
- [ ] Ajouter `{questions}` (Questions clés) pour les prompts de lettre / approche
- [ ] Marquer `cache_control: ephemeral` sur les blocs cachables (cf. §10)

### 11.6. CLI / endpoint `/analyze`
- [ ] Ajouter flag/param `refresh: bool = False`
- [ ] Si `refresh=True` : bypass cache offre (§10) ET versionning analyse (§4.5)

### 11.7. Tests
- [ ] Unit : slugification (§3) — cas accents, caractères spéciaux, troncature
- [ ] Unit : ObsidianWriter — 4 fichiers créés, frontmatter valide YAML
- [ ] Unit : cache offre — skip si URL déjà vue, écrit si nouvelle
- [ ] Unit : cache entité — skip si fichier existe
- [ ] Integration : vault_layout.yaml chargé, paths résolus, docs perso lus
- [ ] E2E : URL réelle → 4 fichiers + 1 fiche entité, ré-exécution = skip

### 11.8. Bases (à faire dans Obsidian, pas l'app)
- [ ] Adapter `Dashboard.base` aux nouveaux chemins (filtre `file.path.startsWith("04_Applications/")` et `file.name.endsWith(".analyse")`)
- [ ] Adapter / créer `Kanban.base` avec `groupBy: status`

---

## 12. Hors scope

- Les frameworks d'analyse, prompts, grilles de scoring restent **dans le repo de l'app** (versionnés en code). Le vault ne stocke que les outils de recherche perso (`06_Resources/Frameworks/`).
- Pas de migration rétroactive du legacy `04_Applications/db/` (archive intouchable).
- Pas de re-génération automatique des fiches entité existantes (`02_Companies/`) — leur format actuel reste tel quel jusqu'à éventuel refresh manuel.
