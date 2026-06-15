"""Audio Generation Provider abstraction"""
from abc import ABC, abstractmethod
from typing import Optional


class AudioGenerationProvider(ABC):
    """Abstract base class for audio generation providers"""
    
    @abstractmethod
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
        pass
    
    @abstractmethod
    def is_available(self) -> bool:
        """
        Check if the audio generation service is available.
        
        Returns:
            True if service is available, False otherwise
        """
        pass
