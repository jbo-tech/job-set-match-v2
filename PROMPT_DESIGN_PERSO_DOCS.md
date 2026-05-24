# Prompt — Design d'injection des docs perso dans une app d'analyse d'offres

## Contexte

Je construis une app Python (FastAPI + Claude API) qui analyse automatiquement des offres d'emploi et génère des lettres de motivation. L'app lit du contenu personnel depuis un vault Obsidian, l'injecte dans les prompts Claude, et écrit les résultats (analyse, lettre, capture PDF) dans le même vault.

## Le matériel personnel disponible

J'ai 5 fichiers markdown riches dans `01_Profilage/` du vault, totalisant ~1597 lignes (≈32 000 tokens) :

- `Mon CV.md` (311 lignes) — CV technique structuré
- `Mes expériences.md` (722 lignes) — toutes les expériences au format narratif détaillé
- `Mon Pitch.md` (150 lignes) — pitch oral court, version "elevator"
- `Profil Professionnel Actualisé 2025.md` (218 lignes) — synthèse consolidée du profil
- `Questions cles.md` (196 lignes) — Q/R types pour entretiens

**Ces fichiers représentent un travail conséquent et précieux**. Je les édite régulièrement, je les considère comme ma "knowledge base" personnelle. Je ne veux **pas** les altérer ou les dégrader pour les besoins de l'app.

## Les besoins de l'app

L'app appelle Claude pour 4 types de tâches, qui ont chacune besoin de **subsets différents** de ce matériel :

| Prompt | Contexte vraiment utile |
|---|---|
| **Analyse d'une offre** (scoring, décision go/no-go) | Profil synthétique + compétences clés |
| **Génération de lettre de motivation** | Pitch + profil + expériences pertinentes (à piocher dans les 722 lignes) |
| **Analyse d'une entreprise cible** | Quasi rien (peut-être profil pour cadrer) |
| **Approche LinkedIn** | Pitch + 1-2 expériences + Q/R types |

## Le problème

Injecter brut les 5 fichiers (~32k tokens) à chaque appel Claude pose 3 problèmes :

1. **Coût** : ~$0.10/call non-cached, $0.01 cached (5min TTL Anthropic). Multiplié par 2-3 calls/offre × 5-10 offres/semaine = supportable mais pas optimal.
2. **Latence** : 32k tokens à parser pour Claude → 2-5s ajoutées par call.
3. **Dilution d'attention** : Claude reçoit du contenu non pertinent à la tâche en cours (ex : 700 lignes d'expériences pour analyser une offre où seules 2-3 expériences comptent). Risque de réponses moins ciblées.

## Les options envisagées

### Option B — Couche "synthèses" dérivées
Garder les fichiers riches intacts (knowledge base). Créer à côté des fichiers courts dérivés (200-500 lignes max) qui sont les seuls injectés. Synchronisation source↔synthèse à la main ou semi-auto.

### Option C — Mapping sélectif par prompt + extraction par section
Garder les fichiers riches intacts. Les structurer avec des sections markdown standardisées (`## Synthèse`, `## Détail`, etc.). La config de l'app mappe chaque prompt aux sections pertinentes. Au runtime, l'app extrait les sections désignées et les concatène.

### Option D — RAG / retrieval par embeddings
Indexer sémantiquement les fichiers (chunks + embeddings, ex. sqlite-vec). Pour chaque appel, embed l'offre, retrieve les top-k chunks pertinents, injecter seulement ceux-là.

## Contraintes

- Outil personnel, utilisateur unique (moi)
- Volume actuel : 5 fichiers, ~32k tokens. Probable de croître modérément (+1-2 fichiers max), pas exponentiellement.
- Fréquence d'usage : 5-10 analyses/semaine
- Stack actuelle : Python 3.12, FastAPI, Pydantic, Claude API (Sonnet 4.6), pas d'infra ML déployée
- Préférence pour la simplicité (pas de sur-ingénierie), pas de magie noire opaque
- L'auditabilité (savoir ce qui est injecté) compte
- Le déterminisme (rejouer un test = même résultat) compte aussi

## Question

Quelle option choisir, et pourquoi ? Si tu vois un angle non couvert (option E, hybride, autre angle), propose-le. Challenge mes hypothèses si elles sont faibles.
