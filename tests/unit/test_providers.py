"""Unit tests for AI providers"""
import pytest
from app.providers.gemini_provider import GeminiProvider
from app.providers.ollama_provider import OllamaProvider
from app.providers.mmaudio_provider import MMAudioProvider
from app.providers.local_image_provider import LocalImageProvider
from app.providers.clipdrop_provider import ClipdropProvider


@pytest.mark.unit
class TestGeminiProvider:
    """Test cases for GeminiProvider"""
    
    @pytest.fixture
    def provider(self):
        """Create GeminiProvider instance"""
        return GeminiProvider()
    
    @pytest.mark.asyncio
    async def test_is_available_no_key(self, provider):
        """Test availability check without API key"""
        # Mock the API key to be empty
        provider.api_key = ""
        result = await provider.is_available()
        assert result is False
    
    @pytest.mark.asyncio
    async def test_analyze_scene_mock(self, provider, sample_text):
        """Test scene analysis with mocked API call"""
        # This would require mocking the HTTP call
        # For now, we test the interface
        assert hasattr(provider, 'analyze_scene')
        assert hasattr(provider, 'check_copyright')
        assert hasattr(provider, 'check_ethics')


@pytest.mark.unit
class TestOllamaProvider:
    """Test cases for OllamaProvider"""
    
    @pytest.fixture
    def provider(self):
        """Create OllamaProvider instance"""
        return OllamaProvider()
    
    @pytest.mark.asyncio
    async def test_is_available(self, provider):
        """Test availability check"""
        result = await provider.is_available()
        # Result depends on whether Ollama is running
        assert isinstance(result, bool)


@pytest.mark.unit
class TestMMAudioProvider:
    """Test cases for MMAudioProvider"""
    
    @pytest.fixture
    def provider(self):
        """Create MMAudioProvider instance"""
        return MMAudioProvider()
    
    @pytest.mark.asyncio
    async def test_is_available(self, provider):
        """Test availability check"""
        result = await provider.is_available()
        # Result depends on whether MMAudio is installed
        assert isinstance(result, bool)


@pytest.mark.unit
class TestLocalImageProvider:
    """Test cases for LocalImageProvider"""
    
    @pytest.fixture
    def provider(self):
        """Create LocalImageProvider instance"""
        return LocalImageProvider()
    
    @pytest.mark.asyncio
    async def test_is_available(self, provider):
        """Test availability check"""
        result = await provider.is_available()
        # Result depends on whether the model is available
        assert isinstance(result, bool)


@pytest.mark.unit
class TestClipdropProvider:
    """Test cases for ClipdropProvider"""
    
    @pytest.fixture
    def provider(self):
        """Create ClipdropProvider instance"""
        return ClipdropProvider()
    
    @pytest.mark.asyncio
    async def test_is_available_no_key(self, provider):
        """Test availability check without API key"""
        provider.api_key = ""
        result = await provider.is_available()
        assert result is False
    
    @pytest.mark.asyncio
    async def test_is_available_with_key(self, provider):
        """Test availability check with API key"""
        provider.api_key = "test_key"
        result = await provider.is_available()
        # This would check if the API is reachable
        assert isinstance(result, bool)
