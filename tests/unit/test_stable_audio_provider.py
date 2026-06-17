"""Unit tests for StableAudioProvider"""
import sys
import types
import pytest
from unittest.mock import Mock, patch, MagicMock

class _FakeTorch(types.ModuleType):
    """Stub module that auto-creates MagicMock attributes and provides a real Tensor type."""
    def __init__(self, name):
        super().__init__(name)
        self._mocks = {}
    def __getattr__(self, name):
        if name == "Tensor":
            return type('Tensor', (), {})
        if name not in self._mocks:
            self._mocks[name] = MagicMock()
        return self._mocks[name]

# Pre-populate heavy modules so tests never touch real torch/torchaudio
sys.modules["torch"] = _FakeTorch("torch")
sys.modules["torch._utils"] = types.ModuleType("torch._utils")
sys.modules["torchaudio"] = _FakeTorch("torchaudio")

# Prevent the real stable_audio_3 submodule from being imported
_fake = types.ModuleType("stable_audio_3")
_fake.StableAudioModel = MagicMock()
sys.modules["stable_audio_3"] = _fake

from app.providers.stable_audio_provider import StableAudioProvider


@pytest.mark.unit
class TestStableAudioProvider:
    """Test cases for StableAudioProvider"""

    @pytest.fixture
    def provider(self):
        return StableAudioProvider()

    @pytest.mark.asyncio
    async def test_generate_audio_passes_negative_prompt(self, provider):
        """negative_prompt should be forwarded to model.generate()."""
        mock_model = MagicMock()
        mock_model.generate.return_value = (MagicMock(), 44100)

        with patch("app.providers.stable_audio_provider._get_model", return_value=mock_model):
            with patch("torchaudio.save"):
                with patch("torch.max", return_value=Mock(item=Mock(return_value=1.0))):
                    with patch("torch.abs"):
                        await provider.generate_audio(
                            prompt="rain sound",
                            duration=8,
                            negative_prompt="music, speech"
                        )

        mock_model.generate.assert_called_once()
        call_kwargs = mock_model.generate.call_args[1]
        assert call_kwargs.get("negative_prompt") == "music, speech"
        assert call_kwargs.get("prompt") == "rain sound"
        assert call_kwargs.get("duration") == 8

    @pytest.mark.asyncio
    async def test_generate_audio_omits_negative_prompt_when_none(self, provider):
        """When negative_prompt is None, it should not be passed to generate()."""
        mock_model = MagicMock()
        mock_model.generate.return_value = (MagicMock(), 44100)

        with patch("app.providers.stable_audio_provider._get_model", return_value=mock_model):
            with patch("torchaudio.save"):
                with patch("torch.max", return_value=Mock(item=Mock(return_value=1.0))):
                    with patch("torch.abs"):
                        await provider.generate_audio(prompt="wind", duration=4)

        call_kwargs = mock_model.generate.call_args[1]
        assert "negative_prompt" not in call_kwargs
