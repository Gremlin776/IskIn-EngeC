"""
LLM client stub for report generation.
"""

from __future__ import annotations

from src.core.config import get_settings
from src.core.logging import get_logger

logger = get_logger(__name__)


class LLMClient:
    """Minimal LLM client wrapper used by ReportService."""

    def __init__(self) -> None:
        self.settings = get_settings()

    async def generate_report(self, prompt: str) -> str:
        """Generate report text using LLM.

        Currently returns a safe placeholder if no external LLM is configured.
        """
        if not self.settings.llm_api_key:
            logger.warning("LLM API key not configured; returning stub report content.")
            return "LLM generation is not configured. Please set LLM_API_KEY."

        # Placeholder for real integration.
        logger.warning("LLM client is a stub; returning placeholder content.")
        return "LLM generation is not implemented."
