"""OutreachGenerator — génère accroche LinkedIn, email intro, suggestions CV.

Pattern identique à CoverLetterGenerator : system prompt + docs perso +
offre + analyse JSON dans le message user. Retourne un OutreachResult structuré.
"""

import json
import logging
import re
from typing import Any

from app.llm.protocol import LLMClient
from app.models import AnalysisResult, OutreachResult
from app.services.document_loader import DocumentLoader
from app.utils.token_logger import log_usage

logger = logging.getLogger(__name__)

SYSTEM_INSTRUCTION = (
    "Tu es un expert en stratégie de candidature. Tu produis des artefacts "
    "d'approche (LinkedIn, email, suggestions CV) en français, en suivant "
    "strictement le format JSON demandé."
)


class OutreachError(RuntimeError):
    """Erreur de génération outreach (API LLM, parsing JSON...)."""


class OutreachGenerator:
    """Génère les artefacts d'approche à partir d'une analyse + offre."""

    def __init__(
        self,
        client: LLMClient,
        doc_loader: DocumentLoader,
        *,
        prompt: str = "",
        max_tokens: int = 4096,
        temperature: float = 0.5,
    ) -> None:
        self.client = client
        self.doc_loader = doc_loader
        self.prompt = prompt
        self.max_tokens = max_tokens
        self.temperature = temperature

    async def generate(self, analysis: AnalysisResult, offer_content: str) -> OutreachResult:
        """Produit les artefacts d'approche."""
        analysis_json = json.dumps(
            analysis.model_dump(mode="json"),
            ensure_ascii=False,
            indent=2,
        )

        user_message = (
            f"## Offre d'emploi\n\n{offer_content}\n\n"
            f"## Analyse structurée de l'offre\n\n"
            f"```json\n{analysis_json}\n```\n\n"
            f"## Instructions\n\n{self.prompt}"
        )

        response = await self.client.complete(
            messages=[{"role": "user", "content": user_message}],
            system=self.doc_loader.build_system_text(SYSTEM_INSTRUCTION),
            system_blocks=self.doc_loader.build_system_blocks(SYSTEM_INSTRUCTION),
            max_tokens=self.max_tokens,
            temperature=self.temperature,
        )

        log_usage(response.usage, "outreach", response.model)

        if not response.text:
            raise OutreachError("Réponse LLM vide pour l'outreach")

        try:
            data = _extract_json(response.text)
            return OutreachResult.model_validate(data)
        except (json.JSONDecodeError, ValueError) as e:
            logger.error(
                "Échec parsing JSON outreach : %s\n--- raw ---\n%s",
                e,
                response.text[:1000],
            )
            raise OutreachError(f"Réponse outreach non parsable : {e}") from e


def _extract_json(text: str) -> dict[str, Any]:
    """Extrait le premier objet JSON valide du texte."""
    text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    fence = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if fence:
        return json.loads(fence.group(1))

    start = text.find("{")
    end = text.rfind("}")
    if start >= 0 and end > start:
        return json.loads(text[start : end + 1])

    raise ValueError("Aucun JSON trouvé dans la réponse outreach")
