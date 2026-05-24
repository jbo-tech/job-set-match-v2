"""GENERATION_PROMPT — génère une lettre de motivation en français (200-260 mots).

V2 : prompt en français, 1 exemple (Beta.gouv DIALOG), directives de ton
issues du profil de personnalité, règles anti-hallucination préservées.
"""

GENERATION_PROMPT = """
**Objectif** : Rédiger la meilleure lettre de motivation possible pour mon profil.

## CONTRÔLE DES SOURCES

1. Informations sur l'offre :
- Utiliser UNIQUEMENT les informations explicitement mentionnées dans l'offre
- NE PAS inventer de besoins non mentionnés dans l'offre
- Reprendre les mots-clés et la terminologie exacte de l'offre

2. Parcours du candidat :
- Référencer UNIQUEMENT les expériences et compétences documentées dans le CV/profil fourni
- Utiliser des réalisations spécifiques avec des métriques réelles
- Ne mapper que les compétences techniques réellement documentées

3. Règles strictes :
- Chaque affirmation doit être traçable à l'offre OU aux documents candidat
- Pas de suppositions génériques sur le secteur
- Pas d'informations spéculatives sur l'entreprise
- Pas de réalisations extrapolées
- Pas de compétences techniques supposées
- Privilégier les formulations verbatim de l'offre

VÉRIFICATION :
Avant de générer, vérifier :
□ Toute information entreprise vient de l'offre
□ Toute affirmation candidat est documentée dans le CV/profil
□ Toute compétence technique mentionnée est prouvée
□ Toutes les métriques et réalisations sont réelles
□ Aucune information spéculative ou supposée

<instructions>
Rédiger une lettre de motivation concise et percutante pour un candidat en reconversion vers la Data Science / IA.

### Identité narrative

- Parcours : pilotage de transformation digitale → Data Science / IA
- Pont : l'expertise métier rencontre la compétence technique
- Différenciateur : double regard stratégique et technique, agilité d'apprentissage prouvée

### Structure

1. **Accroche (15%)** — Ouvrir par l'enjeu de l'entreprise ou un constat terrain. JAMAIS par "je". Montrer la compréhension du contexte et créer un pont naturel vers le profil.

2. **Connexion (25%)** — Choisir l'angle le plus pertinent :
   - Actualité / défi de l'entreprise
   - Réalisation passée en écho avec le poste (problème → solution → résultat)
   - Vision partagée sur l'évolution du secteur

3. **Démonstration (40%)** — Mapper les missions de l'offre aux expériences. Format Contexte → Action → Résultat mesurable. Utiliser des triptyques (3 compétences, 3 étapes, 3 apports). Montrer une compréhension réaliste du challenge.

4. **Projection et fermeture (20%)** — Se projeter dans le poste : proposer des pistes d'action concrètes. Fermer par une question spécifique sur un enjeu du poste (PAS de formule générique type "ravi d'échanger sur ma contribution potentielle").

### Ancres narratives

Histoires de référence à disposition. Choisir 1-2 ancres pertinentes pour le poste et les approfondir. NE PAS les empiler mécaniquement.

| Ancre | Chiffres | Illustre |
|-------|----------|----------|
| Direction pôle 13 experts | réorganisation, 100% objectifs | Management, conduite du changement |
| Écosystème 20 sites / 1M utilisateurs | consolidation, refonte data-first | Vision stratégique, pilotage complexe |
| Tableaux de bord Looker | adoption équipes, décision data-driven | Culture data, autonomisation |
| Solutions nocode (Airtable, Zapier) | réduction coûts, autonomie | Innovation pragmatique, POC |
| Facturation 60%→90% | optimisation processus | Résolution de problèmes, mesure |
| Formation Data Science (Le Wagon) | Python, ML, DL | Transition, capacité d'apprentissage |

### Ton et style

Privilégier la **voix authentique** : directe, humble, engagée. Assume les limites ("je sais que je commence à construire mon expérience") et exprime l'enthousiasme sans le lisser.

**Caractéristiques du ton** :
- Direct et diplomate — affirmer les convictions sans agressivité ("je suis convaincu que…"), poser les constats factuellement avant de proposer
- Registre professionnel soutenu, vocabulaire précis sans jargon excessif — accessible à des interlocuteurs non-techniques
- Argumentation par l'exemple concret et le résultat chiffré, rarement par l'abstraction
- Registre émotionnel contenu — conviction et enthousiasme sans emphase ni superlatifs
- La lettre doit montrer qu'on a écouté (compris l'offre) avant de parler

**Figures autorisées** :
- Métaphores simples : "pont", "créateur de ponts", "faire parler les données"
- Oppositions dialectiques : problème → opportunité
- Triptyques (3 éléments)

### Pièges à éviter

- **Recyclage mécanique** : empiler toujours les mêmes histoires CNIEL sans les adapter — choisir 1-2 ancres et les approfondir
- **Fermetures génériques** : "ravi d'échanger sur ma contribution potentielle" — préférer une question ciblée
- **Perte de la voix authentique** : les lettres trop lissées sont les moins mémorables — garder de l'engagement personnel, de la lucidité sur le parcours
- **Narration linéaire** : un déroulé chronologique est moins convaincant qu'un mapping compétences ↔ besoins
- **Superlatifs et buzzwords** : éviter "passionné", "dynamique", "force de proposition"

### Formulations à éviter

- "Je suis particulièrement passionné/enthousiaste par…"
- "J'ai démontré ma capacité à…"
- "Je suis convaincu que mon profil…"
- Affirmations génériques sur la "valeur ajoutée" ou la "performance"

### Formulations à préférer

- "Ce poste m'intéresse parce que…" + raison spécifique
- "Au [entreprise], j'ai…" + réalisation concrète
- "Mon parcours en X combiné à Y…" + application spécifique
- Affirmations directes liées à des expériences passées

<example>
Madame, Monsieur,

La numérisation des arrêtés de circulation représente un levier pertinent pour la mobilité durable et la logistique urbaine. En permettant l'intégration de ces données dans les GPS et systèmes d'information routière, DIALOG répond à des enjeux concrets : optimisation des itinéraires poids lourds, déploiement efficace des ZFE, et gestion intelligente des restrictions temporaires comme celles prévues pour les JOP.

L'opportunité d'accompagner l'équipe DIALOG en tant que chef de projet innovations et numérique m'intéresse particulièrement car elle conjugue méthodologie agile, vision produit et impact concret sur le service public.

Au CNIEL, j'ai dirigé un pôle pluridisciplinaire de 13 experts (digital, événementiel et graphisme) dans un contexte de réorganisation. En parallèle, j'ai initié et porté transversalement la transformation de l'écosystème digital (1M visiteurs/an) en m'appuyant au maximum sur les données. Cette expérience m'a permis de développer trois compétences intéressantes pour ce poste :
- La gestion de projet en mode agile et le pilotage budgétaire,
- La vision d'ensemble sur l'articulation entre les besoins métiers et les solutions techniques, essentielle pour intégrer DIALOG dans l'écosystème des collectivités et des services d'information routière
- La communication stratégique à haut niveau sur des projets innovants, exercée auprès de la direction générale et des comités interprofessionnels

Ma double expertise - 10 ans de pilotage de projets numériques et une formation récente en Data Science - me permettrait d'accompagner efficacement DIALOG dans ses prochaines étapes de développement :
- Accélérer l'adoption par les collectivités grâce à une méthodologie de conduite du changement
- Valoriser les données collectées pour maximiser l'impact du service
- Explorer et déployer de nouveaux cas d'usage à forte valeur ajoutée, notamment pour la gestion des ZFE

Je suis particulièrement motivé par la possibilité de contribuer à un service public numérique innovant, en m'appuyant sur la méthode beta.gouv que je suis avec intérêt. Je serais ravi d'échanger sur ma vision pour DIALOG et mes motivations.

Cordialement,
</example>

Pourquoi cet exemple fonctionne :
- Ouvre par l'enjeu (numérisation des arrêtés), pas par "je"
- Mapping point-par-point (missions de l'offre → expériences)
- Projection concrète dans le poste (3 pistes d'action pour DIALOG)
- Triptyque structurant (3 compétences, 3 projections)
- Voix authentique : engagement sans emphase
</instructions>

## SPÉCIFICATIONS DE SORTIE

- Longueur : 200-260 mots
- Langue : français uniquement
- Paragraphes structurés
- Mots-clés stratégiques de l'offre intégrés naturellement
- Cohérence narrative d'un paragraphe à l'autre
"""
