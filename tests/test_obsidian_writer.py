"""Tests pour ObsidianWriter R2 (artefacts plats, slug Obsidian, versioning)."""

from datetime import date
from pathlib import Path

import pytest
import yaml

from app.models import (
    AnalysisResult,
    CareerFitAnalysis,
    CompetitiveProfile,
    CvSuggestions,
    EmailIntroduction,
    JobSummary,
    OutreachResult,
    ProfileMatchAssessment,
    ShouldApply,
    StrategicRecommendations,
)
from app.services.obsidian_writer import ObsidianWriter
from app.vault_layout import VaultLayout, VaultPaths


def _make_layout(tmp_path: Path) -> VaultLayout:
    vault = tmp_path / "vault"
    vault.mkdir()
    return VaultLayout(
        vault_root=vault,
        paths=VaultPaths(applications="04_Applications", companies="02_Companies"),
        personal_docs={},
    )


def _make_result(
    company: str = "Acme Corp",
    position: str = "Data Engineer",
    decision: bool = True,
    chance: float = 7.5,
) -> AnalysisResult:
    return AnalysisResult(
        jobSummary=JobSummary(
            jobTitle=position,
            jobCompany=company,
            jobLocation="Paris",
            jobOverview="Description de l'offre",
            jobFailureFactors=["facteur 1"],
            jobPainPointsAnalysis=["pain point 1"],
        ),
        careerFitAnalysis=CareerFitAnalysis(
            careerAnalysis=["analyse carrière"],
            careerDevelopmentRating=8.0,
        ),
        profileMatchAssessment=ProfileMatchAssessment(
            profileMatchAnalysis=["analyse profil"],
            matchCompatibilityRating=7.5,
        ),
        competitiveProfile=CompetitiveProfile(
            competitiveAnalysis=["analyse compétitive"],
            successProbabilityRating=7.0,
        ),
        strategicRecommendations=StrategicRecommendations(
            shouldApply=ShouldApply(
                decision=decision, explanation="Bon match", chanceRating=chance
            ),
            keyPointsInJobOffer=["mot-clé 1"],
            matchingPointsWithProfile=["match 1"],
            keyWordsToUse=["python"],
            preparationSteps="préparer le portfolio",
            interviewFocusAreas="data engineering",
        ),
        offerContent="Texte complet de l'offre",
    )


# --- Structure des artefacts ---


def test_write_creates_flat_artifacts(tmp_path: Path):
    layout = _make_layout(tmp_path)
    writer = ObsidianWriter(layout)
    result = _make_result()
    writer.write(
        result,
        url="https://example.com/job/1",
        offer_content="Contenu de l'offre",
        cover_letter="Madame, Monsieur,",
        pdf_bytes=b"%PDF-1.4 fake",
        offer_date=date(2026, 4, 22),
    )

    apps = layout.vault_root / "04_Applications"
    slug = "Acme Corp - Data Engineer - 2026-04-22"
    assert (apps / f"{slug}.offre.md").exists()
    assert (apps / f"{slug}.analyse.md").exists()
    assert (apps / f"{slug}.lettre.md").exists()
    assert (apps / f"{slug}.pdf").exists()


def test_slug_preserves_spaces_and_accents(tmp_path: Path):
    layout = _make_layout(tmp_path)
    writer = ObsidianWriter(layout)
    result = _make_result(company="Société Générale", position="Ingénieur Data (H/F)")
    writer.write(result, url="https://x.com/1", offer_date=date(2026, 5, 1))

    apps = layout.vault_root / "04_Applications"
    slug = "Société Générale - Ingénieur Data (H_F) - 2026-05-01"
    assert (apps / f"{slug}.analyse.md").exists()


def test_write_without_optional_artifacts(tmp_path: Path):
    layout = _make_layout(tmp_path)
    writer = ObsidianWriter(layout)
    result = _make_result()
    writer.write(result, url="https://example.com/1", offer_date=date(2026, 4, 22))

    apps = layout.vault_root / "04_Applications"
    slug = "Acme Corp - Data Engineer - 2026-04-22"
    assert (apps / f"{slug}.offre.md").exists()
    assert (apps / f"{slug}.analyse.md").exists()
    assert not (apps / f"{slug}.lettre.md").exists()
    assert not (apps / f"{slug}.pdf").exists()


# --- Frontmatter ---


def test_analyse_frontmatter_uses_spec_field_names(tmp_path: Path):
    layout = _make_layout(tmp_path)
    writer = ObsidianWriter(layout)
    result = _make_result()
    writer.write(result, url="https://example.com/1", offer_date=date(2026, 4, 22))

    apps = layout.vault_root / "04_Applications"
    content = (apps / "Acme Corp - Data Engineer - 2026-04-22.analyse.md").read_text()
    fm_text = content.split("---\n")[1]
    fm = yaml.safe_load(fm_text)

    assert fm["type"] == "analyse"
    assert fm["score_interet"] == 8.0
    assert fm["score_adequation"] == 7.5
    assert fm["score_succes"] == 7.0
    assert fm["score_chance"] == 7.5
    assert fm["score_total"] == 30.0
    assert fm["decision"] is True
    assert fm["status"] == "pending"
    assert fm["entreprise"] == "[[02_Companies/Acme Corp]]"


def test_analyse_frontmatter_includes_attribution(tmp_path: Path):
    """analysis_meta (version prompt + modèle + température + coût) atterrit en frontmatter."""
    layout = _make_layout(tmp_path)
    writer = ObsidianWriter(layout)
    result = _make_result()
    writer.write(
        result,
        url="https://example.com/1",
        offer_date=date(2026, 4, 22),
        analysis_meta={
            "prompt_version": "a1b2c3d4",
            "model": "claude-sonnet-4-20250514",
            "temperature": 0.2,
            "cost_usd": 0.0123,
        },
    )
    apps = layout.vault_root / "04_Applications"
    fm = yaml.safe_load(
        (apps / "Acme Corp - Data Engineer - 2026-04-22.analyse.md")
        .read_text()
        .split("---\n")[1]
    )
    assert fm["prompt_version"] == "a1b2c3d4"
    assert fm["model"] == "claude-sonnet-4-20250514"
    assert fm["temperature"] == 0.2
    assert fm["cost_usd"] == 0.0123


def test_analyse_frontmatter_without_attribution(tmp_path: Path):
    """Sans analysis_meta, aucune clé d'attribution n'est ajoutée (rétro-compat)."""
    layout = _make_layout(tmp_path)
    writer = ObsidianWriter(layout)
    writer.write(_make_result(), url="https://example.com/1", offer_date=date(2026, 4, 22))
    apps = layout.vault_root / "04_Applications"
    fm = yaml.safe_load(
        (apps / "Acme Corp - Data Engineer - 2026-04-22.analyse.md")
        .read_text()
        .split("---\n")[1]
    )
    assert "prompt_version" not in fm
    assert "model" not in fm


def test_offre_frontmatter(tmp_path: Path):
    layout = _make_layout(tmp_path)
    writer = ObsidianWriter(layout)
    result = _make_result()
    writer.write(
        result,
        url="https://www.welcometothejungle.com/fr/companies/acme/jobs/data",
        offer_content="Le contenu",
        offer_date=date(2026, 4, 22),
    )

    apps = layout.vault_root / "04_Applications"
    content = (apps / "Acme Corp - Data Engineer - 2026-04-22.offre.md").read_text()
    fm_text = content.split("---\n")[1]
    fm = yaml.safe_load(fm_text)

    assert fm["type"] == "offre"
    assert fm["source"] == "www.welcometothejungle.com"
    assert fm["poste"] == "Data Engineer"
    assert "Le contenu" in content


def test_lettre_frontmatter(tmp_path: Path):
    layout = _make_layout(tmp_path)
    writer = ObsidianWriter(layout)
    result = _make_result()
    writer.write(
        result,
        url="https://x.com/1",
        cover_letter="Cher recruteur,",
        offer_date=date(2026, 4, 22),
    )

    apps = layout.vault_root / "04_Applications"
    content = (apps / "Acme Corp - Data Engineer - 2026-04-22.lettre.md").read_text()
    fm_text = content.split("---\n")[1]
    fm = yaml.safe_load(fm_text)

    assert fm["type"] == "lettre"
    assert fm["lettre_status"] == "draft"
    assert fm["sent_at"] is None
    assert "Cher recruteur," in content


# --- Cache et versioning ---


def test_url_already_analyzed(tmp_path: Path):
    layout = _make_layout(tmp_path)
    writer = ObsidianWriter(layout)
    result = _make_result()

    assert not writer.url_already_analyzed("https://example.com/job/1")
    writer.write(result, url="https://example.com/job/1", offer_date=date(2026, 4, 22))
    assert writer.url_already_analyzed("https://example.com/job/1")
    assert not writer.url_already_analyzed("https://example.com/job/2")


def test_offre_md_not_overwritten(tmp_path: Path):
    layout = _make_layout(tmp_path)
    writer = ObsidianWriter(layout)
    result = _make_result()

    writer.write(result, url="https://x.com/1", offer_content="V1", offer_date=date(2026, 4, 22))
    writer.write(result, url="https://x.com/1", offer_content="V2", offer_date=date(2026, 4, 22))

    apps = layout.vault_root / "04_Applications"
    content = (apps / "Acme Corp - Data Engineer - 2026-04-22.offre.md").read_text()
    assert "V1" in content
    assert "V2" not in content


def test_analyse_versioning(tmp_path: Path):
    layout = _make_layout(tmp_path)
    writer = ObsidianWriter(layout)
    result = _make_result()

    writer.write(result, url="https://x.com/1", offer_date=date(2026, 4, 22))
    writer.write(result, url="https://x.com/2", offer_date=date(2026, 4, 22))

    apps = layout.vault_root / "04_Applications"
    slug = "Acme Corp - Data Engineer - 2026-04-22"
    assert (apps / f"{slug}.analyse.md").exists()
    assert (apps / f"{slug}.analyse.v2.md").exists()


# --- Company ---


def test_company_md_created_in_companies_dir(tmp_path: Path):
    layout = _make_layout(tmp_path)
    writer = ObsidianWriter(layout)
    result = _make_result()
    writer.write(
        result,
        url="https://x.com/1",
        company_report="# Acme Corp\nRapport",
        offer_date=date(2026, 4, 22),
    )

    companies = layout.vault_root / "02_Companies"
    assert (companies / "Acme Corp.md").exists()
    assert "Rapport" in (companies / "Acme Corp.md").read_text()


def test_company_md_not_overwritten(tmp_path: Path):
    layout = _make_layout(tmp_path)
    writer = ObsidianWriter(layout)
    result = _make_result()

    writer.write(
        result, url="https://x.com/1", company_report="V1", offer_date=date(2026, 4, 22)
    )
    writer.write(
        result, url="https://x.com/2", company_report="V2", offer_date=date(2026, 4, 22)
    )

    companies = layout.vault_root / "02_Companies"
    assert "V1" in (companies / "Acme Corp.md").read_text()


# --- Sécurité ---


def test_path_traversal_blocked(tmp_path: Path):
    layout = _make_layout(tmp_path)
    writer = ObsidianWriter(layout)
    result = _make_result(company="../../etc")
    folder = writer.write(result, url="https://x.com/1", offer_date=date(2026, 4, 22))
    assert str(folder.resolve()).startswith(str(layout.vault_root.resolve()))


def test_company_exists_true(tmp_path: Path):
    layout = _make_layout(tmp_path)
    writer = ObsidianWriter(layout)
    companies = layout.vault_root / "02_Companies"
    companies.mkdir()
    (companies / "Acme Corp.md").write_text("# Acme Corp")

    assert writer.company_exists("Acme Corp") is True


def test_company_exists_false(tmp_path: Path):
    layout = _make_layout(tmp_path)
    writer = ObsidianWriter(layout)

    assert writer.company_exists("Acme Corp") is False


def test_company_exists_uses_vault_slug(tmp_path: Path):
    layout = _make_layout(tmp_path)
    writer = ObsidianWriter(layout)
    companies = layout.vault_root / "02_Companies"
    companies.mkdir()
    (companies / "Société Générale.md").write_text("# SG")

    assert writer.company_exists("Société Générale") is True
    assert writer.company_exists("Acme") is False


def test_score_total_calculation():
    result = _make_result()
    assert result.score_total == 30.0


# --- URL index ---


def test_url_index_built_at_init(tmp_path: Path):
    """L'index est construit au démarrage à partir des offre.md existantes."""
    layout = _make_layout(tmp_path)
    writer = ObsidianWriter(layout)
    result = _make_result()
    writer.write(result, url="https://example.com/job/99", offer_date=date(2026, 5, 10))

    writer2 = ObsidianWriter(layout)
    assert writer2.url_already_analyzed("https://example.com/job/99")
    assert not writer2.url_already_analyzed("https://example.com/job/other")


def test_url_index_updated_on_write(tmp_path: Path):
    """Après écriture, l'index est mis à jour sans re-scan."""
    layout = _make_layout(tmp_path)
    writer = ObsidianWriter(layout)
    result = _make_result()

    assert not writer.url_already_analyzed("https://example.com/new")
    writer.write(result, url="https://example.com/new", offer_date=date(2026, 5, 10))
    assert writer.url_already_analyzed("https://example.com/new")


# --- Slug collision unknown ---


def test_slug_collision_unknown_segments(tmp_path: Path):
    """Deux offres même jour avec company/position vides → fichiers distincts."""
    layout = _make_layout(tmp_path)
    writer = ObsidianWriter(layout)
    result1 = _make_result(company="", position="")
    result2 = _make_result(company="", position="")

    writer.write(result1, url="https://a.com/1", offer_date=date(2026, 5, 10))
    writer.write(result2, url="https://b.com/2", offer_date=date(2026, 5, 10))

    apps = layout.vault_root / "04_Applications"
    offre_files = list(apps.glob("*.offre.md"))
    assert len(offre_files) == 2


def test_slug_normal_no_hash(tmp_path: Path):
    """Offres normales n'ont pas de suffixe hash."""
    layout = _make_layout(tmp_path)
    writer = ObsidianWriter(layout)
    result = _make_result(company="Acme Corp", position="Data Engineer")
    writer.write(result, url="https://x.com/1", offer_date=date(2026, 5, 10))

    apps = layout.vault_root / "04_Applications"
    expected = "Acme Corp - Data Engineer - 2026-05-10.offre.md"
    assert (apps / expected).exists()


# --- Outreach ---


def test_lettre_includes_outreach(tmp_path: Path):
    layout = _make_layout(tmp_path)
    writer = ObsidianWriter(layout)
    result = _make_result()
    outreach = OutreachResult(
        accroche_linkedin="Bonjour, votre travail m'intéresse.",
        email_introduction=EmailIntroduction(
            objet="Candidature Data Engineer",
            corps="Bonjour, je me permets de vous contacter.",
        ),
        suggestions_cv=CvSuggestions(
            mots_cles=["Python", "ETL"],
            experiences_a_valoriser=["Direction pôle 13 experts"],
            competences_a_mettre_en_avant=["Gestion de projet"],
            ajustements_recommandes=["Ajouter section data"],
        ),
    )
    writer.write(
        result,
        url="https://x.com/1",
        cover_letter="Madame, Monsieur,",
        outreach=outreach,
        offer_date=date(2026, 5, 24),
    )

    apps = layout.vault_root / "04_Applications"
    content = (apps / "Acme Corp - Data Engineer - 2026-05-24.lettre.md").read_text()
    assert "## Lettre de motivation" in content
    assert "Madame, Monsieur," in content
    assert "## Accroche LinkedIn" in content
    assert "Bonjour, votre travail" in content
    assert "## Email d'introduction" in content
    assert "Candidature Data Engineer" in content
    assert "## Suggestions CV" in content
    assert "`Python`" in content
    assert "Direction pôle 13 experts" in content
    assert "Ajouter section data" in content


def test_lettre_outreach_only(tmp_path: Path):
    """Outreach sans lettre crée quand même le fichier."""
    layout = _make_layout(tmp_path)
    writer = ObsidianWriter(layout)
    result = _make_result()
    outreach = OutreachResult(
        accroche_linkedin="Hello",
    )
    writer.write(
        result,
        url="https://x.com/1",
        outreach=outreach,
        offer_date=date(2026, 5, 24),
    )

    apps = layout.vault_root / "04_Applications"
    content = (apps / "Acme Corp - Data Engineer - 2026-05-24.lettre.md").read_text()
    assert "## Accroche LinkedIn" in content
    assert "## Lettre de motivation" not in content
