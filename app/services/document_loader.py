"""Chargement des documents personnels depuis le vault Obsidian.

Source de vérité : `config.yaml` > vault.personal_docs (§6 spec). Chaque entrée
peut pointer vers un fichier unique ou un motif glob (ex: split d'expériences
par poste). Le loader résout le glob en runtime, lit chaque fichier et
concatène le contenu sous une seule clé.

API :
    loader.load() -> dict[str, str]
        Retourne `{key: contenu concaténé}` pour chaque doc perso déclaré.

    loader.build_system_blocks(system_instruction) -> list[dict]
        Construit la liste system messages prête pour l'API Anthropic, en
        séparant les docs cacheables (cache_control ephemeral) des
        non-cacheables (renvoyés à chaque appel sans cache).
"""

from __future__ import annotations

import logging

from app.vault_layout import VaultLayout

logger = logging.getLogger(__name__)


def _xml_escape(text: str) -> str:
    """Échappement minimal pour insertion dans un bloc XML."""
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


def _wrap_documents_xml(docs: dict[str, str]) -> str:
    """Wrappe un dict {key: contenu} en bloc `<documents>...</documents>`."""
    parts = []
    for idx, (key, content) in enumerate(docs.items(), start=1):
        escaped = _xml_escape(content)
        parts.append(
            f'<document index="{idx}">'
            f"<source>{key}</source>"
            f"<document_content>{escaped}</document_content>"
            f"</document>"
        )
    return f"<documents>{''.join(parts)}</documents>"


class DocumentLoader:
    """Charge les documents perso depuis vault_layout. Cache en mémoire."""

    def __init__(self, vault_layout: VaultLayout) -> None:
        self.vault_layout = vault_layout
        self._dict_cache: dict[str, str] | None = None

    def load(self) -> dict[str, str]:
        """Retourne `{key: contenu}` pour chaque doc perso déclaré.

        Pour les entrées glob, les fichiers matchés sont triés alphabétiquement
        et concaténés (séparateur `\\n\\n`). Les fichiers absents génèrent un
        warning sans interrompre le chargement.
        """
        if self._dict_cache is not None:
            return self._dict_cache

        result: dict[str, str] = {}
        for key in self.vault_layout.personal_docs:
            paths = self.vault_layout.resolve_doc(key)
            contents = []
            for path in paths:
                if not path.exists():
                    logger.warning("Doc perso manquant : %s (clé '%s')", path, key)
                    continue
                contents.append(path.read_text(encoding="utf-8"))
            result[key] = "\n\n".join(contents)

        logger.info(
            "Documents perso chargés : %d clés, %d non vides",
            len(result),
            sum(1 for v in result.values() if v),
        )
        self._dict_cache = result
        return result

    def build_system_blocks(self, system_instruction: str) -> list[dict]:
        """Construit la liste system messages pour Anthropic API.

        Format :
        1. SYSTEM_INSTRUCTION (texte fixe, sans cache)
        2. Docs cacheables (XML wrapper, `cache_control: ephemeral`)
        3. Docs non-cacheables (XML wrapper, sans cache — renvoyés à chaque
           appel ; ex: questions clés qui varient peu mais ne valent pas
           le cache breakpoint)

        Le breakpoint cache Claude est placé à la fin du bloc 2, garantissant
        que le contenu fixe (CV, expériences, pitch, profil) reste mis en cache
        d'un appel à l'autre.
        """
        docs = self.load()

        cacheable: dict[str, str] = {}
        non_cacheable: dict[str, str] = {}
        for key, content in docs.items():
            if not content:
                continue
            if self.vault_layout.personal_docs[key].cache:
                cacheable[key] = content
            else:
                non_cacheable[key] = content

        blocks: list[dict] = [{"type": "text", "text": system_instruction}]

        if cacheable:
            blocks.append(
                {
                    "type": "text",
                    "text": _wrap_documents_xml(cacheable),
                    "cache_control": {"type": "ephemeral"},
                }
            )

        if non_cacheable:
            blocks.append(
                {
                    "type": "text",
                    "text": _wrap_documents_xml(non_cacheable),
                }
            )

        return blocks

    def build_system_text(self, system_instruction: str) -> str:
        """Build a plain-text system prompt (for non-Anthropic providers).

        Concatenates instruction + all docs as XML, ignoring cache flags.
        """
        docs = self.load()
        non_empty = {k: v for k, v in docs.items() if v}
        if not non_empty:
            return system_instruction
        return f"{system_instruction}\n\n{_wrap_documents_xml(non_empty)}"

    def get(self, key: str) -> str:
        """Raccourci pour `load()[key]`. Retourne `""` si la clé est inconnue."""
        return self.load().get(key, "")

    def invalidate(self) -> None:
        """Force le rechargement au prochain `load()`."""
        self._dict_cache = None
