"""Tests pour PromptLoader (vault → fallback Python)."""

from pathlib import Path

import pytest

from app.services.prompt_loader import PromptLoader, _clean_prompt
from app.vault_layout import VaultLayout, VaultPaths


def _make_layout(tmp_path: Path, prompts: dict[str, str] | None = None) -> VaultLayout:
    vault = tmp_path / "vault"
    vault.mkdir()
    return VaultLayout(
        vault_root=vault,
        paths=VaultPaths(),
        personal_docs={},
        prompts=prompts or {},
    )


class TestCleanPrompt:

    def test_strips_frontmatter(self):
        raw = "---\ncreated: 2026-01-01\n---\n\nContenu du prompt"
        assert _clean_prompt(raw) == "Contenu du prompt"

    def test_strips_heading_after_frontmatter(self):
        raw = "---\nkey: val\n---\n\n# Mon titre\n\nContenu"
        assert _clean_prompt(raw) == "Contenu"

    def test_strips_code_fence(self):
        raw = "---\nkey: val\n---\n\n# Titre\n\n```bash\nContenu dans code\n```"
        assert _clean_prompt(raw) == "Contenu dans code"

    def test_preserves_inner_code_fences(self):
        raw = "Instruction\n\n```json\n{\"key\": 1}\n```\n\nSuite"
        assert "```json" in _clean_prompt(raw)
        assert "Suite" in _clean_prompt(raw)

    def test_no_frontmatter(self):
        assert _clean_prompt("Just text") == "Just text"


class TestPromptLoader:

    def test_loads_from_vault(self, tmp_path):
        layout = _make_layout(tmp_path, {"generation": "prompts/gen.md"})
        prompt_dir = layout.vault_root / "prompts"
        prompt_dir.mkdir()
        (prompt_dir / "gen.md").write_text(
            "---\ncreated: 2026-01-01\n---\n\n# Prompt lettre\n\nContenu du prompt vault"
        )

        loader = PromptLoader(layout)
        result = loader.load("generation")

        assert result == "Contenu du prompt vault"

    def test_caches_result(self, tmp_path):
        layout = _make_layout(tmp_path, {"generation": "prompts/gen.md"})
        prompt_dir = layout.vault_root / "prompts"
        prompt_dir.mkdir()
        (prompt_dir / "gen.md").write_text("---\nk: v\n---\n\n# T\n\nOriginal")

        loader = PromptLoader(layout)
        first = loader.load("generation")

        (prompt_dir / "gen.md").write_text("---\nk: v\n---\n\n# T\n\nModifié")
        second = loader.load("generation")

        assert first == second == "Original"

    def test_invalidate_clears_cache(self, tmp_path):
        layout = _make_layout(tmp_path, {"generation": "prompts/gen.md"})
        prompt_dir = layout.vault_root / "prompts"
        prompt_dir.mkdir()
        (prompt_dir / "gen.md").write_text("---\nk: v\n---\n\n# T\n\nOriginal")

        loader = PromptLoader(layout)
        loader.load("generation")

        (prompt_dir / "gen.md").write_text("---\nk: v\n---\n\n# T\n\nModifié")
        loader.invalidate("generation")
        result = loader.load("generation")

        assert result == "Modifié"

    def test_falls_back_to_python_when_file_missing(self, tmp_path):
        layout = _make_layout(tmp_path, {"generation": "missing/gen.md"})
        loader = PromptLoader(layout)
        result = loader.load("generation")

        assert len(result) > 0
        assert "cover letter" in result.lower() or "lettre" in result.lower()

    def test_falls_back_when_key_not_in_prompts(self, tmp_path):
        layout = _make_layout(tmp_path)
        loader = PromptLoader(layout)
        result = loader.load("analysis")

        assert len(result) > 0
        assert "JSON" in result

    def test_unknown_key_raises(self, tmp_path):
        layout = _make_layout(tmp_path)
        loader = PromptLoader(layout)

        with pytest.raises(KeyError, match="inconnu"):
            loader.load("nonexistent")

    def test_vault_prompt_with_code_fence(self, tmp_path):
        layout = _make_layout(tmp_path, {"analysis": "p.md"})
        (layout.vault_root / "p.md").write_text(
            "---\nk: v\n---\n\n# Titre\n\n```bash,python\nContenu prompt\n```"
        )

        loader = PromptLoader(layout)
        assert loader.load("analysis") == "Contenu prompt"

    def test_empty_file_falls_back(self, tmp_path):
        layout = _make_layout(tmp_path, {"generation": "empty.md"})
        (layout.vault_root / "empty.md").write_text("---\nk: v\n---\n\n# Titre\n\n")

        loader = PromptLoader(layout)
        result = loader.load("generation")
        assert len(result) > 0
