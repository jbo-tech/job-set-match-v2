"""Écriture des résultats d'analyse dans le vault Obsidian.

Crée 4 artefacts plats dans `{vault_root}/{paths.applications}/` :
  {slug}.offre.md, {slug}.analyse.md, {slug}.lettre.md, {slug}.pdf

Slug : `{Entreprise} - {Poste} - {YYYY-MM-DD}` (espaces et accents préservés).

Garde-fous :
- Slugification des segments (vault_slug)
- Vérification path traversal via Path.resolve()
- Cache anti-redondance par URL (scan des *.offre.md existants)
- Versioning analyse (.analyse.v2.md, .v3.md…)
"""

import hashlib
import logging
from datetime import date
from pathlib import Path

import yaml

from app.models import AnalysisResult, OutreachResult
from app.utils.paths import ensure_within, vault_slug
from app.vault_layout import VaultLayout

logger = logging.getLogger(__name__)


class ObsidianWriter:
    """Persiste les artefacts d'analyse dans le vault Obsidian."""

    def __init__(self, layout: VaultLayout) -> None:
        self.vault_root = layout.vault_root
        self.apps_dir = self.vault_root / layout.paths.applications
        self.companies_dir = self.vault_root / layout.paths.companies
        self._url_index: dict[str, Path] = {}
        self._build_url_index()

    def _build_url_index(self) -> None:
        """Construit l'index URL → fichier offre au démarrage (scan unique)."""
        if not self.apps_dir.exists():
            return
        for offre_file in self.apps_dir.glob("*.offre.md"):
            try:
                fm = self._read_frontmatter(offre_file)
                if fm and fm.get("url"):
                    self._url_index[fm["url"]] = offre_file
            except Exception:
                continue
        if self._url_index:
            logger.info("Index URL chargé : %d offres existantes", len(self._url_index))

    def company_exists(self, company_name: str) -> bool:
        """Vérifie si une fiche entité existe déjà pour cette entreprise."""
        if not self.companies_dir.exists():
            return False
        filename = f"{vault_slug(company_name)}.md"
        return (self.companies_dir / filename).exists()

    def url_already_analyzed(self, url: str) -> bool:
        """Vérifie si une offre avec cette URL existe déjà dans le vault (O(1))."""
        return url in self._url_index

    def write(
        self,
        result: AnalysisResult,
        url: str,
        offer_content: str = "",
        company_report: str | None = None,
        cover_letter: str | None = None,
        outreach: OutreachResult | None = None,
        pdf_bytes: bytes | None = None,
        offer_date: date | None = None,
    ) -> Path:
        """Écrit les artefacts dans le vault. Retourne le chemin du dossier applications."""
        offer_date = offer_date or date.today()
        company = vault_slug(result.jobSummary.jobCompany, max_length=80)
        position = vault_slug(result.jobSummary.jobTitle, max_length=80)
        slug = f"{company} - {position} - {offer_date.isoformat()}"
        if company == "unknown" or position == "unknown":
            short_hash = hashlib.sha256(url.encode()).hexdigest()[:4]
            slug = f"{slug}-{short_hash}"

        self.apps_dir.mkdir(parents=True, exist_ok=True)
        ensure_within(self.apps_dir / slug, self.vault_root)

        self._write_offre_md(slug, result, url, offer_content, offer_date)
        self._write_analyse_md(slug, result, url, offer_date)

        if cover_letter or outreach:
            self._write_lettre_md(slug, result, cover_letter, outreach, offer_date)

        if pdf_bytes:
            (self.apps_dir / f"{slug}.pdf").write_bytes(pdf_bytes)

        if company_report:
            self._write_company_md(result.jobSummary.jobCompany, company_report)

        logger.info("Écriture vault : %s", self.apps_dir / slug)
        return self.apps_dir

    def _write_offre_md(
        self,
        slug: str,
        result: AnalysisResult,
        url: str,
        offer_content: str,
        offer_date: date,
    ) -> None:
        target = self.apps_dir / f"{slug}.offre.md"
        if target.exists():
            logger.info("offre.md déjà existant, skip : %s", target.name)
            return

        js = result.jobSummary
        company_link = f"[[{self.companies_dir.name}/{vault_slug(js.jobCompany)}]]"
        frontmatter = {
            "type": "offre",
            "slug": slug,
            "url": url,
            "source": _extract_domain(url),
            "extracted_at": offer_date,
            "entreprise": company_link,
            "poste": js.jobTitle,
            "localisation": js.jobLocation,
        }
        body = f"# [{js.jobCompany}] {js.jobTitle}\n\n"
        body += f"{company_link} — {js.jobLocation}\n\n"
        body += offer_content or result.offerContent or ""
        self._write_md(target, frontmatter, body)
        self._url_index[url] = target

    def _write_analyse_md(
        self,
        slug: str,
        result: AnalysisResult,
        url: str,
        offer_date: date,
    ) -> None:
        target = self.apps_dir / f"{slug}.analyse.md"
        if target.exists():
            target = self._next_version(slug)

        js = result.jobSummary
        sr = result.strategicRecommendations
        company_link = f"[[{self.companies_dir.name}/{vault_slug(js.jobCompany)}]]"
        frontmatter = {
            "type": "analyse",
            "slug": slug,
            "entreprise": company_link,
            "poste": js.jobTitle,
            "analyzed_at": offer_date,
            "status": "pending",
            "score_total": result.score_total,
            "score_chance": sr.shouldApply.chanceRating,
            "score_interet": result.careerFitAnalysis.careerDevelopmentRating,
            "score_adequation": result.profileMatchAssessment.matchCompatibilityRating,
            "score_succes": result.competitiveProfile.successProbabilityRating,
            "decision": sr.shouldApply.decision,
        }
        body = _render_analyse_body(result)
        self._write_md(target, frontmatter, body)

    def _write_lettre_md(
        self,
        slug: str,
        result: AnalysisResult,
        cover_letter: str | None,
        outreach: OutreachResult | None,
        offer_date: date,
    ) -> None:
        target = self.apps_dir / f"{slug}.lettre.md"
        js = result.jobSummary
        company_link = f"[[{self.companies_dir.name}/{vault_slug(js.jobCompany)}]]"
        frontmatter = {
            "type": "lettre",
            "slug": slug,
            "entreprise": company_link,
            "poste": js.jobTitle,
            "generated_at": offer_date,
            "lettre_status": "draft",
            "sent_at": None,
        }
        body = f"# Candidature — {js.jobTitle} @ {company_link}\n\n"

        if cover_letter:
            body += f"## Lettre de motivation\n\n{cover_letter}\n\n"

        if outreach:
            body += _render_outreach(outreach)

        self._write_md(target, frontmatter, body)

    def _write_company_md(self, company_name: str, report: str) -> None:
        """Écrit la fiche entité dans 02_Companies/ si elle n'existe pas."""
        self.companies_dir.mkdir(parents=True, exist_ok=True)
        filename = f"{vault_slug(company_name)}.md"
        target = self.companies_dir / filename
        if target.exists():
            logger.info("Fiche entité existante, skip : %s", target.name)
            return
        target.write_text(report, encoding="utf-8")
        logger.info("Fiche entité créée : %s", target.name)

    def _next_version(self, slug: str) -> Path:
        """Trouve le prochain suffixe de version pour .analyse.vN.md."""
        for i in range(2, 100):
            candidate = self.apps_dir / f"{slug}.analyse.v{i}.md"
            if not candidate.exists():
                logger.warning("Analyse déjà existante — versioning : %s", candidate.name)
                return candidate
        raise RuntimeError(f"Trop de versions d'analyse pour {slug}")

    @staticmethod
    def _read_frontmatter(path: Path) -> dict | None:
        """Extrait le frontmatter YAML d'un fichier Markdown."""
        text = path.read_text(encoding="utf-8", errors="replace")
        if not text.startswith("---\n"):
            return None
        end = text.find("\n---\n", 4)
        if end == -1:
            return None
        return yaml.safe_load(text[4:end])

    @staticmethod
    def _write_md(path: Path, frontmatter: dict, body: str) -> None:
        content = (
            "---\n"
            + yaml.safe_dump(frontmatter, allow_unicode=True, sort_keys=False)
            + "---\n\n"
            + body
        )
        path.write_text(content, encoding="utf-8")


def _extract_domain(url: str) -> str:
    """Extrait le domaine d'une URL."""
    from urllib.parse import urlparse
    try:
        return urlparse(url).netloc
    except Exception:
        return ""


def _render_outreach(outreach: OutreachResult) -> str:
    """Génère les sections Markdown pour les artefacts d'approche."""
    parts: list[str] = []

    if outreach.accroche_linkedin:
        parts.append("## Accroche LinkedIn\n")
        parts.append(f"> {outreach.accroche_linkedin}\n")

    email = outreach.email_introduction
    if email.objet or email.corps:
        parts.append("## Email d'introduction\n")
        if email.objet:
            parts.append(f"**Objet** : {email.objet}\n")
        if email.corps:
            parts.append(f"{email.corps}\n")

    cv = outreach.suggestions_cv
    has_cv = cv.mots_cles or cv.experiences_a_valoriser or cv.competences_a_mettre_en_avant or cv.ajustements_recommandes
    if has_cv:
        parts.append("## Suggestions CV\n")
        if cv.mots_cles:
            parts.append("### Mots-clés à intégrer\n")
            parts.append(", ".join(f"`{k}`" for k in cv.mots_cles) + "\n")
        if cv.competences_a_mettre_en_avant:
            parts.append("### Compétences à mettre en avant\n")
            parts.extend(f"- {c}" for c in cv.competences_a_mettre_en_avant)
            parts.append("")
        if cv.experiences_a_valoriser:
            parts.append("### Expériences à valoriser\n")
            parts.extend(f"- {e}" for e in cv.experiences_a_valoriser)
            parts.append("")
        if cv.ajustements_recommandes:
            parts.append("### Ajustements recommandés\n")
            parts.extend(f"- {a}" for a in cv.ajustements_recommandes)
            parts.append("")

    return "\n".join(parts)


def _render_analyse_body(result: AnalysisResult) -> str:
    """Génère le corps Markdown de l'analyse (lecture humaine)."""
    js = result.jobSummary
    sr = result.strategicRecommendations
    parts: list[str] = []

    parts.append(f"# Analyse — {js.jobTitle} @ {js.jobCompany}\n")

    parts.append("## Résumé de l'offre\n")
    parts.append(f"{js.jobOverview}\n")

    if js.jobPainPointsAnalysis:
        parts.append("### Pain points identifiés\n")
        parts.extend(f"- {p}" for p in js.jobPainPointsAnalysis)
        parts.append("")

    if js.jobFailureFactors:
        parts.append("### Facteurs d'échec potentiels\n")
        parts.extend(f"- {f}" for f in js.jobFailureFactors)
        parts.append("")

    parts.append("## Intérêt pour la carrière\n")
    parts.append(f"**Note** : {result.careerFitAnalysis.careerDevelopmentRating}/10\n")
    parts.extend(f"- {c}" for c in result.careerFitAnalysis.careerAnalysis)
    parts.append("")

    parts.append("## Adéquation du profil\n")
    parts.append(f"**Note** : {result.profileMatchAssessment.matchCompatibilityRating}/10\n")
    parts.extend(f"- {c}" for c in result.profileMatchAssessment.profileMatchAnalysis)
    parts.append("")

    parts.append("## Probabilité de succès\n")
    parts.append(f"**Note** : {result.competitiveProfile.successProbabilityRating}/10\n")
    parts.extend(f"- {c}" for c in result.competitiveProfile.competitiveAnalysis)
    parts.append("")

    parts.append("## Décision\n")
    decision_text = "GO" if sr.shouldApply.decision else "NO-GO"
    parts.append(f"**Score total** : {result.score_total}/40 — **{decision_text}**\n")
    parts.append(f"{sr.shouldApply.explanation}\n")

    if sr.keyPointsInJobOffer:
        parts.append("### Points clés de l'offre\n")
        parts.extend(f"- {p}" for p in sr.keyPointsInJobOffer)
        parts.append("")

    if sr.matchingPointsWithProfile:
        parts.append("### Points de match avec mon profil\n")
        parts.extend(f"- {p}" for p in sr.matchingPointsWithProfile)
        parts.append("")

    if sr.keyWordsToUse:
        parts.append("### Mots-clés à utiliser\n")
        parts.append(", ".join(f"`{k}`" for k in sr.keyWordsToUse) + "\n")

    if sr.preparationSteps:
        parts.append("### Étapes de préparation\n")
        parts.append(f"{sr.preparationSteps}\n")

    if sr.interviewFocusAreas:
        parts.append("### Points d'attention en entretien\n")
        parts.append(f"{sr.interviewFocusAreas}\n")

    parts.append("## Sources\n")
    parts.append(f"- [[{result.jobSummary.jobCompany} - {result.jobSummary.jobTitle}.offre]]\n")

    parts.append("<!-- ZONE LIBRE — annotations manuelles ci-dessous, jamais touchée par l'app -->\n")

    return "\n".join(parts)
