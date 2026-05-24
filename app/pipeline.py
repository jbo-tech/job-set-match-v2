"""Orchestrateur central — exécute le pipeline d'analyse complet.

Étapes :
    1. Fetch fallback si contenu plugin trop court (Phase 3)
    2. En parallèle :
        - Analyse offre via LLM (OfferAnalyzer)
        - Capture PDF via Playwright (best-effort)
    3. Analyse entreprise via LLM + Brave Search (séquentielle, dépend du nom)
    4. Score gate (chance rating)
    5. (Phase 4) génération lettre si decision == True
    6. Écriture vault Obsidian
"""

import asyncio
import logging

from app.config import Settings
from app.llm import create_llm_client
from app.models import AnalysisResult, AnalyzeRequest, AnalyzeResponse
from app.services.company_analyzer import CompanyAnalyzer
from app.services.content_fetcher import ContentFetcher
from app.services.cover_letter import CoverLetterGenerator
from app.services.document_loader import DocumentLoader
from app.models import OutreachResult
from app.services.obsidian_writer import ObsidianWriter
from app.services.offer_analyzer import AnalysisError, OfferAnalyzer
from app.services.outreach_generator import OutreachGenerator
from app.services.prompt_loader import PromptLoader
from app.utils.token_logger import get_stats
from app.vault_layout import get_vault_layout

logger = logging.getLogger(__name__)

MIN_CONTENT_LENGTH = 200


class Pipeline:
    """Pipeline d'analyse réutilisable (instancié une fois au démarrage)."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.vault_layout = get_vault_layout()
        self.doc_loader = DocumentLoader(self.vault_layout)
        self.prompt_loader = PromptLoader(self.vault_layout)

        api_keys = settings.api_keys

        analysis_client = create_llm_client(settings.resolve_model("analysis"), api_keys)
        company_client = create_llm_client(settings.resolve_model("company"), api_keys)
        generation_client = create_llm_client(settings.resolve_model("generation"), api_keys)

        self.offer_analyzer = OfferAnalyzer(
            analysis_client,
            self.doc_loader,
            prompt=self.prompt_loader.load("analysis"),
            max_tokens=settings.max_tokens,
            temperature=settings.analysis_temperature,
        )
        self.content_fetcher = ContentFetcher()
        self.company_analyzer = CompanyAnalyzer(
            company_client,
            self.doc_loader,
            prompt=self.prompt_loader.load("company"),
            brave_api_key=settings.brave_api_key,
            max_tokens=settings.max_tokens,
            temperature=settings.analysis_temperature,
        )
        self.cover_letter_generator = CoverLetterGenerator(
            generation_client,
            self.doc_loader,
            prompt=self.prompt_loader.load("generation"),
            max_tokens=settings.max_tokens,
            temperature=settings.generation_temperature,
        )
        self.outreach_generator = OutreachGenerator(
            generation_client,
            self.doc_loader,
            prompt=self.prompt_loader.load("outreach"),
            max_tokens=4096,
            temperature=0.5,
        )
        self.obsidian_writer = ObsidianWriter(self.vault_layout)

    async def run(self, request: AnalyzeRequest) -> AnalyzeResponse:
        """Exécute le pipeline complet sur une requête d'analyse."""
        try:
            cost_before = get_stats().cost_usd
            url_str = str(request.url)
            refresh = request.refresh
            logger.info("Analyse démarrée : %s (refresh=%s)", url_str, refresh)

            content = await self._maybe_fetch_fallback(request, url_str)

            if not refresh and self.obsidian_writer.url_already_analyzed(url_str):
                logger.info("URL déjà analysée dans le vault, skip : %s", url_str)
                return AnalyzeResponse(status="deduplicated")

            analysis, pdf_bytes = await self._analyze_and_capture(content, url_str)

            company_name = analysis.jobSummary.jobCompany
            if not refresh and self.obsidian_writer.company_exists(company_name):
                logger.info("Fiche entité existante, skip CompanyAnalyzer : %s", company_name)
                company_report = None
            else:
                company_report = await self._analyze_company(company_name)

            should_generate_letter = _should_generate_letter(
                analysis, self.settings.score_threshold
            )
            logger.info(
                "Décision : %s (chance=%s, generate_letter=%s)",
                analysis.strategicRecommendations.shouldApply.decision,
                analysis.strategicRecommendations.shouldApply.chanceRating,
                should_generate_letter,
            )

            cover_letter = None
            outreach = None
            if should_generate_letter:
                cover_letter, outreach = await self._generate_all(analysis, content)

            vault_path = self.obsidian_writer.write(
                result=analysis,
                url=url_str,
                offer_content=content,
                company_report=company_report,
                cover_letter=cover_letter,
                outreach=outreach,
                pdf_bytes=pdf_bytes,
            )

            run_cost = round(get_stats().cost_usd - cost_before, 6)

            return AnalyzeResponse(
                status="success",
                company=analysis.jobSummary.jobCompany,
                position=analysis.jobSummary.jobTitle,
                decision=analysis.strategicRecommendations.shouldApply.decision,
                score_total=analysis.score_total,
                chance_rating=analysis.strategicRecommendations.shouldApply.chanceRating,
                cost_usd=run_cost,
                vault_path=str(vault_path),
            )

        except AnalysisError as e:
            logger.exception("Échec analyse LLM")
            return AnalyzeResponse(status="error", error=str(e))
        except Exception as e:  # pragma: no cover - filet de sécurité
            logger.exception("Erreur pipeline inattendue")
            return AnalyzeResponse(status="error", error=f"{type(e).__name__}: {e}")

    # ------------------------------------------------------------------ étapes

    async def _maybe_fetch_fallback(self, request: AnalyzeRequest, url: str) -> str:
        """Si le contenu plugin est trop court, tenter un fetch HTTP direct."""
        content = request.content
        needs_fetch = request.needs_fetch or len(content) < MIN_CONTENT_LENGTH
        if not needs_fetch:
            return content

        logger.info("Contenu plugin trop court (%d chars) — fetch fallback", len(content))
        fetched = await self.content_fetcher.fetch_clean_text(url)
        if fetched and len(fetched) > len(content):
            logger.info("Fetch fallback OK : %d chars", len(fetched))
            return fetched
        logger.warning("Fetch fallback indisponible — utilisation contenu plugin")
        return content

    async def _analyze_and_capture(
        self, content: str, url: str
    ) -> tuple[AnalysisResult, bytes | None]:
        """Lance analyse offre et capture PDF en parallèle."""
        results = await asyncio.gather(
            self.offer_analyzer.analyze(content, url),
            self.content_fetcher.capture_pdf(url),
            return_exceptions=True,
        )
        analysis_result, pdf_result = results

        if isinstance(analysis_result, BaseException):
            if isinstance(analysis_result, AnalysisError):
                raise analysis_result
            raise AnalysisError(f"Erreur analyse offre : {analysis_result}") from analysis_result

        if isinstance(pdf_result, BaseException):
            logger.warning("Capture PDF échec : %s", pdf_result)
            pdf_bytes: bytes | None = None
        else:
            pdf_bytes = pdf_result

        return analysis_result, pdf_bytes

    async def _analyze_company(self, company_name: str) -> str | None:
        """Analyse l'entreprise (best-effort)."""
        try:
            return await self.company_analyzer.analyze(company_name)
        except Exception as e:
            logger.warning("CompanyAnalyzer échec : %s", e)
            return None

    async def _generate_all(
        self, analysis: AnalysisResult, offer_content: str
    ) -> tuple[str | None, OutreachResult | None]:
        """Génère lettre + outreach en parallèle (best-effort)."""
        results = await asyncio.gather(
            self._generate_cover_letter(analysis, offer_content),
            self._generate_outreach(analysis, offer_content),
            return_exceptions=True,
        )
        letter_result, outreach_result = results

        cover_letter = None if isinstance(letter_result, BaseException) else letter_result
        outreach = None if isinstance(outreach_result, BaseException) else outreach_result

        if isinstance(letter_result, BaseException):
            logger.warning("CoverLetterGenerator échec : %s", letter_result)
        if isinstance(outreach_result, BaseException):
            logger.warning("OutreachGenerator échec : %s", outreach_result)

        return cover_letter, outreach

    async def _generate_cover_letter(
        self, analysis: AnalysisResult, offer_content: str
    ) -> str | None:
        """Génère la lettre de motivation (best-effort)."""
        try:
            return await self.cover_letter_generator.generate(analysis, offer_content)
        except Exception as e:
            logger.warning("CoverLetterGenerator échec : %s", e)
            return None

    async def _generate_outreach(
        self, analysis: AnalysisResult, offer_content: str
    ) -> OutreachResult | None:
        """Génère les artefacts d'approche (best-effort)."""
        try:
            return await self.outreach_generator.generate(analysis, offer_content)
        except Exception as e:
            logger.warning("OutreachGenerator échec : %s", e)
            return None


def _should_generate_letter(result: AnalysisResult, threshold: float) -> bool:
    """Détermine si la lettre doit être générée."""
    sa = result.strategicRecommendations.shouldApply
    if threshold <= 0:
        return sa.decision
    return sa.decision and sa.chanceRating >= threshold
