"""Tests pour app.utils.paths : safe_slug, vault_slug et ensure_within."""

from pathlib import Path

import pytest

from app.utils.paths import ensure_within, safe_slug, vault_slug


# --- safe_slug ---------------------------------------------------------------


def test_safe_slug_basic():
    assert safe_slug("Acme Corp") == "Acme-Corp"


def test_safe_slug_special_chars_removed():
    assert safe_slug("Data Engineer / Senior") == "Data-Engineer-Senior"


def test_safe_slug_traversal_attempt():
    # Le slugify doit éliminer les caractères dangereux comme ../
    result = safe_slug("../../../etc/passwd")
    assert "/" not in result
    assert ".." not in result


def test_safe_slug_empty_uses_fallback():
    assert safe_slug("", fallback="default") == "default"
    assert safe_slug("///", fallback="default") == "default"


def test_safe_slug_accents():
    assert safe_slug("Société Générale") == "Societe-Generale"


# --- vault_slug --------------------------------------------------------------


def test_vault_slug_preserves_spaces_and_accents():
    assert vault_slug("Société Générale") == "Société Générale"


def test_vault_slug_replaces_unsafe_chars():
    assert vault_slug("Data Engineer / Senior") == "Data Engineer _ Senior"
    assert vault_slug('titre: "important"') == "titre- 'important'"
    assert vault_slug("A|B\\C*D?E<F>G") == "A-B_C_DEFG"


def test_vault_slug_truncates():
    assert len(vault_slug("x" * 200, max_length=80)) == 80


def test_vault_slug_empty_fallback():
    assert vault_slug("???") == "unknown"


def test_vault_slug_collapses_whitespace():
    assert vault_slug("  too   many   spaces  ") == "too many spaces"


# --- ensure_within -----------------------------------------------------------


def test_ensure_within_valid(tmp_path: Path):
    parent = tmp_path / "vault"
    parent.mkdir()
    child = parent / "subdir" / "file.md"
    result = ensure_within(child, parent)
    assert str(result).startswith(str(parent.resolve()))


def test_ensure_within_traversal_blocked(tmp_path: Path):
    parent = tmp_path / "vault"
    parent.mkdir()
    bad = parent / ".." / "evil.md"
    with pytest.raises(ValueError, match="Path traversal"):
        ensure_within(bad, parent)


def test_ensure_within_absolute_outside(tmp_path: Path):
    parent = tmp_path / "vault"
    parent.mkdir()
    bad = Path("/etc/passwd")
    with pytest.raises(ValueError, match="Path traversal"):
        ensure_within(bad, parent)
