"""Stable Audio 3 Small SFX implementation of AudioGenerationProvider"""
import sys
import uuid
from pathlib import Path
from typing import Optional

# Allow importing from local git submodule without pip install
_sys_path_add = str(Path(__file__).parent.parent.parent / "stable-audio-3")
if _sys_path_add not in sys.path:
    sys.path.insert(0, _sys_path_add)

from huggingface_hub import login

from app.providers.audio_provider import AudioGenerationProvider
from app.utils.api_logger import ApiCallTimer
from app.utils.logger import get_logger

logger = get_logger("vibetale")

_model = None


def _get_model():
    global _model
    if _model is None:
        from config import settings
        from stable_audio_3 import StableAudioModel
        if settings.hf_token:
            login(token=settings.hf_token)
        model_name = settings.stable_audio_model
        logger.info(f"Loading Stable Audio 3: {model_name}")
        with ApiCallTimer("StableAudio", "from_pretrained", f"model={model_name}") as t:
            _model = StableAudioModel.from_pretrained(model_name)
            t.status = "loaded"
        logger.info("Stable Audio 3 loaded.")
    return _model


class StableAudioProvider(AudioGenerationProvider):
    """Stable Audio 3 Small SFX provider."""

    async def generate_audio(self, prompt: str, duration: int = 8, negative_prompt: Optional[str] = None) -> str:
        import torch
        import torchaudio

        model = _get_model()

        with ApiCallTimer("StableAudio", "generate", f"duration={duration}s") as t:
            audio = model.generate(prompt=prompt, duration=duration)
            t.status = "ok"

        output_path = Path(f"/tmp/audio_{uuid.uuid4()}.wav")
        sr = 44100

        if isinstance(audio, tuple):
            audio, sr = audio

        if not isinstance(audio, torch.Tensor):
            audio = torch.tensor(audio)

        audio = audio.cpu().to(torch.float32)

        # Ensure [channels, samples] for torchaudio.save
        if audio.dim() == 1:
            audio = audio.unsqueeze(0)
        elif audio.dim() == 3:
            audio = audio[0] if audio.shape[0] > 1 else audio.squeeze(0)
        elif audio.dim() == 2 and audio.shape[0] > 2:
            audio = audio.transpose(0, 1)

        if audio.dim() != 2:
            audio = audio.view(1, -1)

        peak = torch.max(torch.abs(audio)) or 1
        audio = (audio / peak).clamp(-1, 1)

        torchaudio.save(str(output_path), audio, sr)
        logger.info(f"Audio saved to {output_path}")
        return str(output_path)

    def is_available(self) -> bool:
        try:
            import stable_audio_3
            return True
        except ImportError:
            return False
