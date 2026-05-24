"""Schémas Pydantic — contrats partagés entre plugin, backend et vault."""

from __future__ import annotations

from pydantic import BaseModel, Field, HttpUrl


# =============================================================================
# Requête entrante depuis le plugin Firefox
# =============================================================================


class AnalyzeRequest(BaseModel):
    """Payload reçu depuis l'extension Firefox."""

    url: HttpUrl
    title: str
    content: str = Field(
        ...,
        max_length=50_000,
        description="Texte extrait de la page (body.innerText)",
    )
    needs_fetch: bool = Field(
        default=False,
        description="True si l'extension a flag le contenu comme trop court (< 200 chars)",
    )
    refresh: bool = Field(
        default=False,
        description="True pour forcer la ré-analyse (bypass caches URL et entité)",
    )


# =============================================================================
# Sous-modèles du résultat ANALYSIS_PROMPT
# =============================================================================


class JobSummary(BaseModel):
    """Section 1 — résumé de l'offre."""

    jobTitle: str = ""
    jobCompany: str = ""
    jobLocation: str = ""
    jobOverview: str = ""
    jobFailureFactors: list[str] = Field(default_factory=list)
    jobPainPointsAnalysis: list[str] = Field(default_factory=list)


class CareerFitAnalysis(BaseModel):
    """Section 2 — alignement avec la trajectoire de carrière."""

    careerAnalysis: list[str] = Field(default_factory=list)
    careerDevelopmentRating: float = 0.0


class ProfileMatchAssessment(BaseModel):
    """Section 3 — adéquation profil/offre."""

    profileMatchAnalysis: list[str] = Field(default_factory=list)
    matchCompatibilityRating: float = 0.0


class CompetitiveProfile(BaseModel):
    """Section 4 — différenciation compétitive."""

    competitiveAnalysis: list[str] = Field(default_factory=list)
    successProbabilityRating: float = 0.0


class ShouldApply(BaseModel):
    """Décision go/no-go."""

    decision: bool = False
    explanation: str = ""
    chanceRating: float = 0.0


class StrategicRecommendations(BaseModel):
    """Section 5 — recommandations stratégiques."""

    shouldApply: ShouldApply = Field(default_factory=ShouldApply)
    keyPointsInJobOffer: list[str] = Field(default_factory=list)
    matchingPointsWithProfile: list[str] = Field(default_factory=list)
    keyWordsToUse: list[str] = Field(default_factory=list)
    preparationSteps: str = ""
    interviewFocusAreas: str = ""


class AnalysisResult(BaseModel):
    """Résultat complet retourné par ANALYSIS_PROMPT (parsé depuis JSON Claude)."""

    jobSummary: JobSummary
    careerFitAnalysis: CareerFitAnalysis
    profileMatchAssessment: ProfileMatchAssessment
    competitiveProfile: CompetitiveProfile
    strategicRecommendations: StrategicRecommendations
    offerContent: str = ""

    @property
    def score_total(self) -> float:
        """Somme des 4 scores principaux (sur 40)."""
        return round(
            self.careerFitAnalysis.careerDevelopmentRating
            + self.profileMatchAssessment.matchCompatibilityRating
            + self.competitiveProfile.successProbabilityRating
            + self.strategicRecommendations.shouldApply.chanceRating,
            1,
        )


# =============================================================================
# Outreach — accroche LinkedIn, email, suggestions CV
# =============================================================================


class EmailIntroduction(BaseModel):
    """Email d'introduction structuré."""

    objet: str = ""
    corps: str = ""


class CvSuggestions(BaseModel):
    """Suggestions d'ajustement CV pour une offre spécifique."""

    mots_cles: list[str] = Field(default_factory=list)
    experiences_a_valoriser: list[str] = Field(default_factory=list)
    competences_a_mettre_en_avant: list[str] = Field(default_factory=list)
    ajustements_recommandes: list[str] = Field(default_factory=list)


class OutreachResult(BaseModel):
    """Résultat de la génération d'artefacts d'approche."""

    accroche_linkedin: str = ""
    email_introduction: EmailIntroduction = Field(default_factory=EmailIntroduction)
    suggestions_cv: CvSuggestions = Field(default_factory=CvSuggestions)


# =============================================================================
# Réponse renvoyée à l'extension Firefox
# =============================================================================


class AnalyzeResponse(BaseModel):
    """Réponse synthétique pour le popup du plugin."""

    status: str = Field(..., description="success | deduplicated | error")
    company: str | None = None
    position: str | None = None
    decision: bool | None = None
    score_total: float | None = None
    chance_rating: float | None = None
    cost_usd: float | None = None
    vault_path: str | None = None
    error: str | None = None
