# Anti-patterns

Erreurs rencontrées et comment les éviter. Ajoutés via `/retro`.

<!-- Format :
### [Titre court]
**Problème** : Ce qui s'est mal passé
**Cause** : Pourquoi
**Solution** : Comment corriger/éviter
**Date** : YYYY-MM-DD
-->

### log_usage() charge get_settings() en import-time
**Problème** : Les tests unitaires de CompanyAnalyzer et CoverLetterGenerator échouent car `log_usage()` appelle `get_settings()` qui exige toutes les env vars (OBSIDIAN_VAULT_PATH, ANTHROPIC_API_KEY, etc.).
**Cause** : `log_usage()` fait `settings = get_settings()` à chaque appel pour lire les coûts tokens. Dans les tests, pas de `.env` → Pydantic ValidationError.
**Solution** : Monkeypatch `log_usage` avec un fixture `autouse=True` dans chaque fichier de test qui touche un service appelant Claude. Alternative future : découpler les coûts de get_settings() ou passer les coûts en paramètre.
**Date** : 2026-04-13

### Suivre une spec sans vérifier l'état réel du code
**Problème** : `APP_INTEGRATION_SPEC.md` §11.5 décrivait une migration de placeholders `{bio}`, `{competences}` etc. dans les prompts. Au moment d'implémenter, les prompts (analysis.py, generation.py) n'avaient JAMAIS contenu de placeholders nommés — la spec décrivait un état imaginé, pas l'état réel du code.
**Cause** : La spec a été rédigée à distance du code. Le code utilisait en réalité un XML wrapper `<documents><document><source>bio</source>…</document>…</documents>` injecté en bloc, sans templating Python.
**Solution** : Avant d'implémenter une checklist de spec, vérifier l'état réel du code (`grep` les variables, lire les services concernés). Ré-cadrer le travail si la spec et le code divergent. Documenter la découverte plutôt que de forcer l'alignement.
**Date** : 2026-05-14

### Coûts tokens hardcodés désynchronisés du modèle réel
**Problème** : `config.py` hardcodait des coûts de Claude 3.5 Sonnet ($3/M, $15/M) alors que le modèle configuré était `claude-sonnet-4-20250514`. De plus, les tokens de cache (`cache_creation_input_tokens`, `cache_read_input_tokens`) n'étaient pas comptabilisés du tout malgré le prompt caching actif.
**Cause** : Les coûts avaient été copiés depuis la doc Anthropic au moment du setup sans mécanisme de mise à jour. Le prompt caching a été ajouté après (§6.5) sans mettre à jour le calcul de coût.
**Solution** : Résolution dynamique via `pricing.json` (LiteLLM, partagé avec llm-sparring). Le fichier est maintenu à jour via `scripts/refresh_pricing.py` dans sparring. Ne plus jamais hardcoder de tarifs dans le code.
**Date** : 2026-05-19

### CompanyAnalyzer retournait None silencieusement après MAX_ITERATIONS
**Problème** : sur des entités complexes (ex: MEFSIN, entité gouvernementale), Claude cherchait indéfiniment via Brave Search sans jamais produire de `stop_reason != "tool_use"`. Après 8 itérations, le code retournait `None` → pas d'`entreprise.md` dans le vault, 8 appels API gaspillés.
**Cause** : le guard de boucle (`MAX_TOOL_ITERATIONS`) interrompait proprement la boucle mais ne récupérait pas le travail partiel. Claude avait déjà accumulé des résultats de recherche mais n'avait pas l'occasion de les synthétiser.
**Solution** : après la boucle, faire un appel final SANS tools avec un message explicite demandant de conclure. Garantit une sortie textuelle et valorise les recherches déjà faites.
**Date** : 2026-05-19

### Headers HTTP Firefox et caractères non-ASCII
**Problème** : `Window.fetch` dans le service worker Firefox refusait d'envoyer la requête avec l'erreur "Cannot convert value to ByteString because the character at index 100 has value 8212".
**Cause** : le token d'auth copié-collé depuis un éditeur rich-text contenait un em-dash (—, U+2014) au lieu d'un tiret ASCII (-). Firefox impose que les headers HTTP soient des ByteStrings (chars 0-255).
**Solution** : sanitiser les valeurs de headers avec `.replace(/[^\x00-\x7F]/g, "-")` à la sauvegarde (popup) ET à la lecture (service worker). Double protection car l'ancien token peut persister en storage.local.
**Date** : 2026-05-20

### Defaults incohérents entre composants
**Problème** : le port par défaut du plugin (8001) ne correspondait pas au port par défaut du backend (8000 dans config.py). Premier lancement = échec silencieux.
**Cause** : le port avait été changé temporairement pour contourner un processus fantôme sur 8000, puis hardcodé dans le plugin sans aligner les defaults.
**Solution** : toujours aligner les valeurs par défaut entre composants qui communiquent. Quand un workaround temporaire touche un default, le reverter une fois le problème résolu.
**Date** : 2026-05-20
