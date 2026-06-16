"""Stable Audio 3 Small SFX implementation of AudioGenerationProvider"""
import os
import uuid
from pathlib import Path
from typing import Optional

from app.providers.audio_provider import AudioGenerationProvider
from app.utils.logger import get_logger

logger = get_logger("vibetale")

# Lazy singleton for model instance
_model_instance = None
_model_device = None
_model_sample_rate = 44100  # SAME autoencoder: 44.1 kHz stereo


def _get_model():
    """Lazy-load Stable Audio 3 Small SFX model (singleton)."""
    global _model_instance, _model_device
    if _model_instance is None:
        try:
            import torch
            from stable_audio_3 import StableAudioModel
            from config import settings

            device = "cuda" if torch.cuda.is_available() else "cpu"
            logger.info(f"Loading Stable Audio 3 Small SFX on {device} ...")

            # Lokal model klasörü (config.py'deki dosya yolundan klasörü bul)
            model_dir = os.path.dirname(os.path.abspath(settings.stable_audio_model_path))
            logger.info(f"Loading model from local directory: {model_dir}")
            model = StableAudioModel.from_pretrained(model_dir)
            model = model.to(device)

            if device == "cuda":
                model = model.half()  # float16 for VRAM efficiency
                torch.cuda.empty_cache()

            _model_instance = model
            _model_device = device
            logger.info("Stable Audio 3 Small SFX loaded successfully.")
        except ImportError as exc:
            logger.error(
                "stable-audio-3 package not found. "
                "Please clone https://github.com/Stability-AI/stable-audio-3 and install it."
            )
            raise RuntimeError(
                "stable-audio-3 is required. Install: "
                "pip install git+https://github.com/Stability-AI/stable-audio-3.git"
            ) from exc
    return _model_instance


class StableAudioProvider(AudioGenerationProvider):
    """Stable Audio 3 Small SFX provider for ambient audio generation."""

    async def generate_audio(
        self,
        prompt: str,
        duration: int = 8,
        negative_prompt: Optional[str] = None
    ) -> str:
        """
        Generate ambient audio from a text prompt.

        Args:
            prompt: Text description of the desired audio
            duration: Duration in seconds (default: 8)
            negative_prompt: What to avoid in the audio generation

        Returns:
            Path to the generated audio file
        """
        import torch
        import torchaudio

        model = _get_model()
        device = _model_device

        if negative_prompt is None:
            negative_prompt = "music, speech, noise, distortion"

        logger.info(f"Generating {duration}s audio with Stable Audio 3: {prompt[:60]}...")

        with torch.no_grad():
            if device == "cuda":
                with torch.cuda.amp.autocast():
                    audio = model.generate(
                        prompt=prompt,
                        duration=duration
                    )
            else:
                audio = model.generate(
                    prompt=prompt,
                    duration=duration
                )

        # Normalize and save
        output_filename = f"audio_{uuid.uuid4()}.wav"
        output_path = Path("/tmp") / output_filename

        # audio shape handling: ensure [channels, samples]
        if isinstance(audio, tuple):
            audio, sr = audio
        else:
            sr = _model_sample_rate

        if audio.dim() == 1:
            audio = audio.unsqueeze(0)
        elif audio.dim() == 2 and audio.shape[0] > 2:
            audio = audio.transpose(0, 1)

        # Peak normalize
        audio = audio.to(torch.float32)
        peak = torch.max(torch.abs(audio))
        if peak > 0:
            audio = audio / peak
        audio = audio.clamp(-1, 1)

        torchaudio.save(str(output_path), audio.cpu(), sr)
        logger.info(f"Audio saved to {output_path}")

        return str(output_path)

    def is_available(self) -> bool:
        """
        Check if the audio generation service is available.

        Returns:
            True if service is available, False otherwise
        """
        try:
            import stable_audio_3  # noqa: F401
            return True
        except ImportError:
            return False
