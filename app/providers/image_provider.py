"""Image Generation Provider abstraction"""
from abc import ABC, abstractmethod
from typing import Optional


class ImageGenerationProvider(ABC):
    """Abstract base class for image generation providers"""
    
    @abstractmethod
    async def generate_image(
        self,
        prompt: str,
        width: int = 512,
        height: int = 512,
        negative_prompt: Optional[str] = None
    ) -> str:
        """
        Generate an image from a text prompt.
        
        Args:
            prompt: Text description of the desired image
            width: Image width in pixels (default: 512)
            height: Image height in pixels (default: 512)
            negative_prompt: What to avoid in the image generation
            
        Returns:
            Path to the generated image file
        """
        pass
    
    @abstractmethod
    async def is_available(self) -> bool:
        """
        Check if the image generation service is available.
        
        Returns:
            True if service is available, False otherwise
        """
        pass
