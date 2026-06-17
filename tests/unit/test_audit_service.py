"""Unit tests for AuditService"""
import pytest
from app.services.audit_service import AuditService
from app.models.book import AuditResult


@pytest.mark.unit
class TestAuditService:
    """Test cases for AuditService"""
    
    @pytest.fixture
    def audit_service(self, mock_llm_provider):
        """Create AuditService instance with mock LLM"""
        return AuditService(llm_provider=mock_llm_provider)
    
    @pytest.fixture
    def safe_text(self):
        """Safe text for testing"""
        return "This is a harmless story about a boy and his dog."
    
    @pytest.fixture
    def copyright_text(self):
        """Text with potential copyright issues"""
        return "This is the exact text from Harry Potter by J.K. Rowling."
    
    @pytest.fixture
    def unethical_text(self):
        """Text with unethical content"""
        return "This contains hate speech and violence."
    
    @pytest.mark.asyncio
    async def test_audit_safe_content(self, audit_service, safe_text):
        """Safe content (mock returns approved) is approved."""
        result = await audit_service.audit_book(safe_text)
        assert result == AuditResult.APPROVED

    @pytest.mark.asyncio
    async def test_audit_ethics_violation(self, audit_service, mock_llm_provider, unethical_text):
        """Ethics violation maps to ETHICS_VIOLATION."""
        mock_llm_provider.check_ethics.return_value = {"status": "violation", "reason": "hate"}
        result = await audit_service.audit_book(unethical_text)
        assert result == AuditResult.ETHICS_VIOLATION

    @pytest.mark.asyncio
    async def test_audit_copyright_suspicious(self, audit_service, mock_llm_provider, copyright_text):
        """Suspicious copyright maps to COPYRIGHT_SUSPICIOUS."""
        mock_llm_provider.check_copyright.return_value = {"status": "suspicious", "reason": "maybe"}
        result = await audit_service.audit_book(copyright_text)
        assert result == AuditResult.COPYRIGHT_SUSPICIOUS

    @pytest.mark.asyncio
    async def test_audit_failed_provider(self, audit_service, mock_llm_provider, safe_text):
        """Provider failure maps to AUDIT_FAILED."""
        mock_llm_provider.check_copyright.return_value = {"status": "audit_failed", "reason": "err"}
        result = await audit_service.audit_book(safe_text)
        assert result == AuditResult.AUDIT_FAILED

    @pytest.mark.asyncio
    async def test_audit_empty_text(self, audit_service):
        """Empty text still returns a valid AuditResult."""
        result = await audit_service.audit_book("")
        assert isinstance(result, AuditResult)

    def test_sample_text_under_threshold_returns_full(self, audit_service):
        """Short text is returned verbatim (no sampling)."""
        text = "short story"
        assert audit_service._sample_text(text) == text

    def test_sample_text_over_threshold_samples_passages(self, audit_service):
        """Long text is reduced to begin/middle/end passages."""
        text = "A" * 5000 + "B" * 5000 + "C" * 5000
        sample = audit_service._sample_text(text)
        assert len(sample) < len(text)
        assert "[BEGINNING]" in sample and "[MIDDLE]" in sample and "[END]" in sample
