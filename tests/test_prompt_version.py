"""Tests pour l'empreinte automatique de prompt."""

from app.utils.prompt_version import prompt_fingerprint


def test_fingerprint_is_short_hex():
    fp = prompt_fingerprint("Analyse cette offre…")
    assert len(fp) == 8
    assert all(c in "0123456789abcdef" for c in fp)


def test_fingerprint_is_deterministic():
    assert prompt_fingerprint("même texte") == prompt_fingerprint("même texte")


def test_fingerprint_changes_with_text():
    assert prompt_fingerprint("prompt v1") != prompt_fingerprint("prompt v2")
