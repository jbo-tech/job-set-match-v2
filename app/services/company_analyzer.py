"""CompanyAnalyzer — analyse approfondie d'une entreprise via LLM + Brave Search.

Pattern : le LLM pilote la recherche en tool_use. Notre code expose un tool
`brave_search` ; le modèle génère les requêtes pertinentes, on les exécute,
on renvoie les résultats, le modèle itère jusqu'à produire le rapport final
en markdown (selon COMPANY_PROMPT).
"""

import logging

from app.llm.protocol import LLMClient, ToolDefinition, ToolResult
from app.services.brave_search import BraveSearchError, brave_web_search
from app.services.document_loader import DocumentLoader
from app.utils.token_logger import log_usage

logger = logging.getLogger(__name__)

SYSTEM_INSTRUCTION = (
    "Tu es un analyste d'entreprise stratégique qui aide un candidat en "
    "reconversion à évaluer des entreprises cibles. Tu connais le profil "
    "du candidat grâce aux documents personnels fournis. Tu réponds en français."
)

BRAVE_TOOL = ToolDefinition(
    name="brave_search",
    description=(
        "Recherche web via Brave Search. À utiliser pour obtenir des "
        "informations à jour sur une entreprise : taille, secteur, levées "
        "de fonds, stack technique, culture, actualités récentes."
    ),
    input_schema={
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Requête de recherche en français ou anglais",
            }
        },
        "required": ["query"],
    },
)

MAX_TOOL_ITERATIONS = 5


class CompanyAnalyzer:
    """Génère un rapport entreprise en markdown via LLM + Brave Search."""

    def __init__(
        self,
        client: LLMClient,
        doc_loader: DocumentLoader,
        *,
        prompt: str = "",
        brave_api_key: str = "",
        max_tokens: int = 8192,
        temperature: float = 0.2,
    ) -> None:
        self.client = client
        self.doc_loader = doc_loader
        self.prompt = prompt
        self.brave_api_key = brave_api_key
        self.max_tokens = max_tokens
        self.temperature = temperature

    async def analyze(self, company_name: str) -> str | None:
        """Analyse une entreprise et retourne le rapport markdown."""
        if not company_name or not company_name.strip():
            logger.warning("CompanyAnalyzer : nom d'entreprise vide")
            return None

        if not self.brave_api_key:
            logger.warning("CompanyAnalyzer désactivé : BRAVE_API_KEY non configurée")
            return None

        system_text = self.doc_loader.build_system_text(SYSTEM_INSTRUCTION)
        system_blocks = self.doc_loader.build_system_blocks(SYSTEM_INSTRUCTION)

        messages: list[dict] = [
            {
                "role": "user",
                "content": (
                    f"Analyse l'entreprise suivante : **{company_name}**\n\n"
                    f"Utilise l'outil `brave_search` autant de fois que nécessaire "
                    f"pour rassembler les informations, puis produis le rapport final "
                    f"en suivant le format demandé.\n\n"
                    f"{self.prompt}"
                ),
            }
        ]

        try:
            for iteration in range(MAX_TOOL_ITERATIONS):
                response = await self.client.complete_with_tools(
                    messages=messages,
                    system=system_text,
                    system_blocks=system_blocks,
                    tools=[BRAVE_TOOL],
                    max_tokens=self.max_tokens,
                    temperature=self.temperature,
                )
                log_usage(response.usage, f"company.iter{iteration}", response.model)

                if response.stop_reason != "tool_use":
                    return response.text or None

                messages.append(self.client.format_assistant_message(response))
                tool_results = await self._execute_tools(response)
                messages.extend(self.client.format_tool_results(tool_results))

            logger.warning(
                "CompanyAnalyzer : limite de %d itérations atteinte, forçage du rapport final",
                MAX_TOOL_ITERATIONS,
            )
            messages.append({
                "role": "user",
                "content": (
                    "Tu as atteint la limite de recherches. Produis maintenant "
                    "le rapport final en markdown avec les informations déjà collectées. "
                    "Ne fais plus de recherche."
                ),
            })
            final = await self.client.complete(
                messages=messages,
                system=system_text,
                system_blocks=system_blocks,
                max_tokens=self.max_tokens,
                temperature=self.temperature,
            )
            log_usage(final.usage, "company.final", final.model)
            return final.text or None

        except Exception as e:
            logger.exception("CompanyAnalyzer erreur : %s", e)
            return None

    async def _execute_tools(self, response) -> list[ToolResult]:
        """Execute tool calls and return results."""
        results = []
        for tc in response.tool_calls:
            if tc.name != "brave_search":
                results.append(ToolResult(
                    tool_call_id=tc.id, content="Tool inconnu", is_error=True,
                ))
                continue

            query = tc.arguments.get("query", "")
            logger.info("CompanyAnalyzer : recherche '%s'", query)
            try:
                content = await brave_web_search(query, self.brave_api_key)
                results.append(ToolResult(tool_call_id=tc.id, content=content))
            except BraveSearchError as e:
                results.append(ToolResult(
                    tool_call_id=tc.id,
                    content=f"Erreur Brave Search : {e}",
                    is_error=True,
                ))
        return results
