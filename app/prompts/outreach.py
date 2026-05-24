"""OUTREACH_PROMPT — génère accroche LinkedIn, email d'introduction, suggestions CV."""

OUTREACH_PROMPT = """
**Objectif** : Produire 3 artefacts d'approche pour accompagner une candidature.

## CONTRÔLE DES SOURCES
- Chaque affirmation doit être traçable à l'offre d'emploi OU aux documents candidat fournis
- Pas d'informations inventées, pas de suppositions sur l'entreprise au-delà de l'offre
- Les mots-clés suggérés doivent venir de l'offre (verbatim quand possible)

## ARTEFACTS À PRODUIRE

### 1. Accroche LinkedIn (message de connexion)
- **Longueur** : 280 caractères maximum (limite LinkedIn)
- **Ton** : professionnel mais chaleureux, personnalisé
- **Structure** : contexte commun ou intérêt spécifique → lien avec le poste → proposition d'échange
- **Interdits** : formules creuses ("votre parcours m'inspire"), flatterie excessive, demander directement le poste
- Le message doit donner envie d'accepter la connexion, pas de répondre en détail

### 2. Email d'introduction
- **Longueur** : 80-120 mots
- **Ton** : direct, concret, respectueux du temps du destinataire
- **Structure** :
  - Objet (court, spécifique au poste)
  - 1 phrase de contexte (pourquoi vous écrivez)
  - 1-2 phrases sur votre valeur ajoutée spécifique pour CE poste
  - 1 phrase de fermeture avec proposition concrète (appel de 15min, café, etc.)
- Plus court et plus direct qu'une lettre de motivation — c'est une prise de contact, pas une argumentation complète

### 3. Suggestions d'ajustement CV
Basé sur l'analyse de l'offre et le profil du candidat, fournir :
- **mots_cles** : 5-8 mots-clés/compétences de l'offre à s'assurer de faire apparaître dans le CV (verbatim de l'offre)
- **experiences_a_valoriser** : 2-3 expériences du candidat les plus pertinentes pour cette offre, avec indication de comment les reformuler/mettre en avant
- **competences_a_mettre_en_avant** : 3-5 compétences du candidat qui matchent les besoins de l'offre (priorisées)
- **ajustements_recommandes** : 1-3 suggestions concrètes de restructuration/reformulation du CV pour ce poste spécifique

## FORMAT DE SORTIE

Répondre UNIQUEMENT en JSON valide, sans texte avant ni après :

```json
{
  "accroche_linkedin": "...",
  "email_introduction": {
    "objet": "...",
    "corps": "..."
  },
  "suggestions_cv": {
    "mots_cles": ["...", "..."],
    "experiences_a_valoriser": ["...", "..."],
    "competences_a_mettre_en_avant": ["...", "..."],
    "ajustements_recommandes": ["...", "..."]
  }
}
```

## LANGUE
Tous les artefacts en français.
"""
