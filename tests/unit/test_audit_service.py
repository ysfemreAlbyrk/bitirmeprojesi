"""Unit tests for AuditService"""
import pytest
from app.services.audit_service import AuditService


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
        """Test auditing safe content"""
        result = await audit_service.audit_content(safe_text)
        
        assert result is not None
        assert "status" in result
        assert result["status"] == "approved"
    
    @pytest.mark.asyncio
    async def test_audit_copyright_content(self, audit_service, copyright_text):
        """Test auditing content with copyright issues"""
        result = await audit_service.audit_content(copyright_text)
        
        assert result is not None
        assert "status" in result
    
    @pytest.mark.asyncio
    async def test_audit_unethical_content(self, audit_service, unethical_text):
        """Test auditing unethical content"""
        result = await audit_service.audit_content(unethical_text)
        
        assert result is not None
        assert "status" in result
    
    @pytest.mark.asyncio
    async def test_audit_empty_text(self, audit_service):
        """Test auditing empty text"""
        result = await audit_service.audit_content("")
        
        assert result is not None
        assert "status" in result
