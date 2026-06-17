"""Pytest configuration and fixtures"""
import pytest
from unittest.mock import Mock, AsyncMock
from app.providers.llm_provider import LLMProvider, SceneAnalysis
from app.providers.audio_provider import AudioGenerationProvider
from app.providers.image_provider import ImageGenerationProvider


@pytest.fixture
def mock_llm_provider():
    """Mock LLM provider for testing (async methods use AsyncMock)."""
    provider = Mock(spec=LLMProvider)

    # Mock scene analysis
    provider.analyze_scene = AsyncMock(return_value=SceneAnalysis(
        scene="test scene",
        emotion="neutral",
        sfx_prompt="ambient sound",
        image_prompt="test image"
    ))

    # Mock copyright check
    provider.check_copyright = AsyncMock(return_value={
        "status": "approved",
        "reason": "No copyright issues",
        "confidence": 0.95
    })

    # Mock ethics check
    provider.check_ethics = AsyncMock(return_value={
        "status": "approved",
        "reason": "No ethical concerns",
        "categories": [],
        "confidence": 0.95
    })

    # Mock scene boundary detection
    provider.detect_scene_boundaries = AsyncMock(return_value=[])

    provider.is_available.return_value = True

    return provider


@pytest.fixture
def mock_audio_provider():
    """Mock audio provider for testing"""
    provider = Mock(spec=AudioGenerationProvider)
    provider.generate_audio = AsyncMock(return_value="/tmp/test_audio.wav")
    provider.is_available.return_value = True
    return provider


@pytest.fixture
def mock_image_provider():
    """Mock image provider for testing"""
    provider = Mock(spec=ImageGenerationProvider)
    provider.generate_image = AsyncMock(return_value="/tmp/test_image.png")
    provider.is_available.return_value = True
    return provider


@pytest.fixture
def sample_text():
    """Sample text for testing"""
    return """
    The sun was setting over the horizon, casting long shadows across the meadow. 
    Birds were singing their evening songs while a gentle breeze rustled through the trees.
    It was a peaceful evening, perfect for a quiet walk.
    """
