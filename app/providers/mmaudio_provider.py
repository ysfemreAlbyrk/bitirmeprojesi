"""MMAudio implementation of AudioGenerationProvider"""
import os
import subprocess
from pathlib import Path
from typing import Optional
from app.providers.audio_provider import AudioGenerationProvider
from config import settings


class MMAudioProvider(AudioGenerationProvider):
    """MMAudio local model implementation for audio generation"""
    
    def __init__(self):
        self.mmaudio_path = Path(settings.mmaudio_path).expanduser()
        self.demo_script = self.mmaudio_path / "demo.py"
    
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
        if negative_prompt is None:
            negative_prompt = "music, speech, noise, distortion"
        
        # Generate unique output filename
        import uuid
        output_filename = f"audio_{uuid.uuid4()}.wav"
        output_path = Path("/tmp") / output_filename
        
        # Build MMAudio command
        cmd = [
            "python",
            str(self.demo_script),
            "--prompt", prompt,
            "--num_steps", "50",
            "--negative_prompt", negative_prompt,
            "--output", str(output_path)
        ]
        
        try:
            # Run MMAudio generation
            process = await subprocess.run(
                cmd,
                cwd=str(self.mmaudio_path),
                capture_output=True,
                text=True,
                check=True
            )
            
            return str(output_path)
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"MMAudio generation failed: {e.stderr}")
    
    async def is_available(self) -> bool:
        """
        Check if the audio generation service is available.
        
        Returns:
            True if service is available, False otherwise
        """
        return (
            self.mmaudio_path.exists() and
            self.demo_script.exists()
        )
