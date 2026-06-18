#!/bin/sh
# sign.sh — fait signer l'extension par Mozilla en canal "unlisted".
#
# La signature unlisted est automatique (quelques minutes) : Mozilla renvoie
# un .xpi signé que tu distribues/installes toi-même, sans listing public sur
# addons.mozilla.org.
#
# Identifiants requis (depuis https://addons.mozilla.org/developers/addon/api/key/) :
#   WEB_EXT_API_KEY     — l'« issuer » JWT
#   WEB_EXT_API_SECRET  — le « secret » JWT
#
# On les lit dans l'environnement (web-ext les consomme nativement) plutôt que
# de les passer en argument : ça évite de les exposer dans la liste des
# processus (ps). Ne jamais committer ces valeurs.
#
# Note : chaque envoi unlisted exige un numéro de version unique. Avant de
# re-signer, incrémente "version" dans plugin/manifest.json.

set -eu

PLUGIN_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)

# --- Vérification des identifiants ---
if [ -z "${WEB_EXT_API_KEY:-}" ] || [ -z "${WEB_EXT_API_SECRET:-}" ]; then
    echo "Erreur : WEB_EXT_API_KEY et WEB_EXT_API_SECRET doivent être définis." >&2
    echo >&2
    echo "  1. Récupère une clé sur https://addons.mozilla.org/developers/addon/api/key/" >&2
    echo "  2. Exporte-la (sans la committer) :" >&2
    echo "       export WEB_EXT_API_KEY=user:xxxxx:123" >&2
    echo "       export WEB_EXT_API_SECRET=xxxxxxxx" >&2
    echo "  3. Relance ./plugin/sign.sh" >&2
    exit 1
fi

# --- Signature (web-ext via npx, version épinglée) ---
# --channel=unlisted : signature auto, distribution privée.
npx --yes web-ext@8 sign \
    --source-dir="$PLUGIN_DIR" \
    --artifacts-dir="$PLUGIN_DIR/web-ext-artifacts" \
    --channel=unlisted

echo
echo "Signature terminée. Le .xpi signé est dans plugin/web-ext-artifacts/."
echo "Installe-le dans Firefox : about:addons → roue crantée → « Installer un module depuis un fichier »."
