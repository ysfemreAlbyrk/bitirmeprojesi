"""Copyright and ethics audit service"""
from typing import Dict, Any
from app.providers.llm_provider import LLMProvider
from app.models.book import AuditResult


class AuditService:
    """Service for auditing uploaded books for copyright and ethical compliance"""
    
    def __init__(self, llm_provider: LLMProvider):
        self.llm_provider = llm_provider
    
    async def audit_book(self, text: str) -> AuditResult:
        """
        Perform full audit on book text (copyright and ethics check).
        
        Args:
            text: Book text to audit
            
        Returns:
            AuditResult indicating the audit outcome
        """
        # Perform both checks in parallel
        copyright_result = await self.llm_provider.check_copyright(text)
        ethics_result = await self.llm_provider.check_ethics(text)
        
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
        copyright_result = await self.llm_provider.check_copyright(text)
        ethics_result = await self.llm_provider.check_ethics(text)
        
        return {
            'copyright': copyright_result,
            'ethics': ethics_result,
            'overall_result': await self.audit_book(text)
        }
