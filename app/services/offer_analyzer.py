"""OfferAnalyzer — appel LLM avec ANALYSIS_PROMPT pour analyser une offre.

Utilise le pattern V1 : system prompt + docs perso (cache_control ephemeral)
+ contenu de l'offre dans le message user. Parse la réponse JSON en
AnalysisResult Pydantic.
"""

import json
import logging
import re
from typing import Any

from app.llm.protocol import LLMClient
from app.models import AnalysisResult
from app.services.document_loader import DocumentLoader
from app.utils.token_logger import log_usage

logger = logging.getLogger(__name__)

SYSTEM_INSTRUCTION = (
    "Tu es un expert en analyse d'offres d'emploi pour un candidat en "
    "reconversion. Tu réponds toujours en français et tu suis strictement "
    "le format JSON demandé."
)


class AnalysisError(RuntimeError):
    """Erreur d'analyse Claude (parsing JSON, validation Pydantic, API)."""


class OfferAnalyzer:
    """Analyse une offre via LLM → AnalysisResult structuré."""

    def __init__(
        self,
        client: LLMClient,
        doc_loader: DocumentLoader,
        *,
        prompt: str = "",
        max_tokens: int = 8192,
        temperature: float = 0.2,
    ) -> None:
        self.client = client
        self.doc_loader = doc_loader
        self.prompt = prompt
        self.max_tokens = max_tokens
        self.temperature = temperature

    async def analyze(self, content: str, url: str) -> AnalysisResult:
        """Envoie l'offre au LLM et retourne le résultat parsé."""
        response = await self.client.complete(
            messages=[
                {
                    "role": "user",
                    "content": (
                        f"URL de l'offre : {url}\n\n"
                        f"Contenu de l'offre :\n{content}\n\n"
                        f"{self.prompt}"
                    ),
                }
            ],
            system=self.doc_loader.build_system_text(SYSTEM_INSTRUCTION),
            system_blocks=self.doc_loader.build_system_blocks(SYSTEM_INSTRUCTION),
            max_tokens=self.max_tokens,
            temperature=self.temperature,
        )

        log_usage(response.usage, "analysis", response.model)

        if not response.text:
            raise AnalysisError("Réponse LLM vide ou inattendue")

        try:
            data = _extract_json(response.text)
            return AnalysisResult.model_validate(data)
        except (json.JSONDecodeError, ValueError) as e:
            logger.error(
                "Échec parsing JSON LLM : %s\n--- raw ---\n%s", e, response.text[:1000]
            )
            raise AnalysisError(f"Réponse LLM non parsable : {e}") from e


def _extract_json(text: str) -> dict[str, Any]:
    """Extrait le premier objet JSON valide du texte."""
    text = text.strip()
    try:
        result = json.loads(text)
        logger.debug("JSON extrait : méthode directe")
        return result
    except json.JSONDecodeError:
        pass

    fence = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if fence:
        logger.debug("JSON extrait : bloc markdown ```json```")
        return json.loads(fence.group(1))

    start = text.find("{")
    end = text.rfind("}")
    if start >= 0 and end > start:
        logger.debug("JSON extrait : sous-chaîne { ... }")
        return json.loads(text[start : end + 1])

    raise ValueError("Aucun JSON trouvé dans la réponse")
