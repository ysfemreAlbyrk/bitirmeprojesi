"""Copyright and ethics audit service"""
import asyncio
from typing import Dict, Any
from app.providers.llm_provider import LLMProvider
from app.models.book import AuditResult


class AuditService:
    """Service for auditing uploaded books for copyright and ethical compliance"""

    # Each sampled passage size (characters) and full-text threshold
    SAMPLE_SIZE = 2000
    FULL_TEXT_THRESHOLD = 6000

    def __init__(self, llm_provider: LLMProvider):
        self.llm_provider = llm_provider

    def _sample_text(self, text: str) -> str:
        """Take representative passages (beginning/middle/end) instead of the
        whole book to avoid LLM context overflow and free-tier rate limits."""
        text = (text or "").strip()
        if len(text) <= self.FULL_TEXT_THRESHOLD:
            return text

        size = self.SAMPLE_SIZE
        mid_start = max(0, (len(text) // 2) - (size // 2))
        beginning = text[:size]
        middle = text[mid_start:mid_start + size]
        end = text[-size:]
        return (
            "[BEGINNING]\n" + beginning +
            "\n\n[MIDDLE]\n" + middle +
            "\n\n[END]\n" + end
        )

    async def audit_book(self, text: str) -> AuditResult:
        """
        Perform full audit on book text (copyright and ethics check).
        
        Args:
            text: Book text to audit
            
        Returns:
            AuditResult indicating the audit outcome
        """
        sample = self._sample_text(text)

        # Run both checks in parallel
        copyright_result, ethics_result = await asyncio.gather(
            self.llm_provider.check_copyright(sample),
            self.llm_provider.check_ethics(sample),
        )
        
        # Determine overall result
        if ethics_result.get('status') == 'violation':
            return AuditResult.ETHICS_VIOLATION
        
        if copyright_result.get('status') == 'violation':
            return AuditResult.COPYRIGHT_SUSPICIOUS
        
        if copyright_result.get('status') == 'suspicious':
            return AuditResult.COPYRIGHT_SUSPICIOUS
        
        if copyright_result.get('status') == 'audit_failed' or ethics_result.get('status') == 'audit_failed':
            return AuditResult.AUDIT_FAILED
        
        return AuditResult.APPROVED
    
    async def get_audit_details(self, text: str) -> Dict[str, Any]:
        """
        Get detailed audit results.
        
        Args:
            text: Book text to audit
            
        Returns:
            Dict with detailed audit information
        """
        sample = self._sample_text(text)
        copyright_result, ethics_result = await asyncio.gather(
            self.llm_provider.check_copyright(sample),
            self.llm_provider.check_ethics(sample),
        )

        return {
            'copyright': copyright_result,
            'ethics': ethics_result,
            'overall_result': await self.audit_book(text)
        }
