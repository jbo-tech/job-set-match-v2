"""CoverLetterGenerator — génère une lettre de motivation via LLM.

Pattern identique à OfferAnalyzer : system prompt + docs perso (cache_control
ephemeral) + offre + analyse JSON dans le message user. La lettre est
retournée en texte brut (200-260 mots, format prescrit par GENERATION_PROMPT).
"""

import json
import logging

from app.llm.protocol import LLMClient
from app.models import AnalysisResult
from app.services.document_loader import DocumentLoader
from app.utils.token_logger import log_usage

logger = logging.getLogger(__name__)

SYSTEM_INSTRUCTION = (
    "Tu es un expert en rédaction de lettres de motivation pour un candidat "
    "en reconversion vers la Data Science / IA. Tu écris uniquement en "
    "français, en suivant strictement les règles anti-hallucination et le "
    "format demandé (200-260 mots)."
)


class CoverLetterError(RuntimeError):
    """Erreur de génération de lettre (API LLM, réponse vide...)."""


class CoverLetterGenerator:
    """Génère une lettre de motivation à partir d'une analyse + offre."""

    def __init__(
        self,
        client: LLMClient,
        doc_loader: DocumentLoader,
        *,
        prompt: str = "",
        max_tokens: int = 8192,
        temperature: float = 0.7,
    ) -> None:
        self.client = client
        self.doc_loader = doc_loader
        self.prompt = prompt
        self.max_tokens = max_tokens
        self.temperature = temperature

    async def generate(self, analysis: AnalysisResult, offer_content: str) -> str:
        """Produit une lettre de motivation en français."""
        analysis_json = json.dumps(
            analysis.model_dump(mode="json"),
            ensure_ascii=False,
            indent=2,
        )

        user_message = (
            f"## Offre d'emploi\n\n{offer_content}\n\n"
            f"## Analyse structurée de l'offre\n\n"
            f"```json\n{analysis_json}\n```\n\n"
            f"## Instructions de génération\n\n{self.prompt}"
        )

        response = await self.client.complete(
            messages=[{"role": "user", "content": user_message}],
            system=self.doc_loader.build_system_text(SYSTEM_INSTRUCTION),
            system_blocks=self.doc_loader.build_system_blocks(SYSTEM_INSTRUCTION),
            max_tokens=self.max_tokens,
            temperature=self.temperature,
        )

        log_usage(response.usage, "cover_letter", response.model)

        if not response.text:
            raise CoverLetterError("Réponse LLM vide pour la lettre")

        letter = response.text.strip()
        if not letter:
            raise CoverLetterError("Lettre générée vide après nettoyage")

        logger.info("Lettre générée : %d caractères", len(letter))
        return letter
