"""Prompts LLM — source de vérité dans le repo."""

from app.prompts.analysis import ANALYSIS_PROMPT
from app.prompts.company import COMPANY_PROMPT
from app.prompts.generation import GENERATION_PROMPT
from app.prompts.outreach import OUTREACH_PROMPT

__all__ = [
    "ANALYSIS_PROMPT",
    "COMPANY_PROMPT",
    "GENERATION_PROMPT",
    "OUTREACH_PROMPT",
]
