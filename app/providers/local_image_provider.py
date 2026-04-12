"""Local image generation implementation of ImageGenerationProvider"""
import os
from pathlib import Path
from typing import Optional
from app.providers.image_provider import ImageGenerationProvider
from config import settings


class LocalImageProvider(ImageGenerationProvider):
    """Local model implementation for image generation (SDXL-Turbo or similar)"""
    
    def __init__(self):
        self.model_path = Path(settings.image_generation_path).expanduser()
        self.model_name = settings.image_generation_model
        self._model = None
    
    def _load_model(self):
        """Lazy load the model"""
        if self._model is None:
            # Import diffusion libraries
            try:
                from diffusers import StableDiffusionXLPipeline
                import torch
                
                # Load model
                self._model = StableDiffusionXLPipeline.from_single_file(
                    str(self.model_path),
                    torch_dtype=torch.float16,
                    variant="fp16"
                )
                
                # Move to GPU if available
                if torch.cuda.is_available():
                    self._model.to("cuda")
            except ImportError:
                raise ImportError(
                    "Diffusers library not installed. "
                    "Install with: pip install diffusers transformers accelerate torch"
                )
    
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
        self._load_model()
        
        # Generate unique output filename
        import uuid
        output_filename = f"image_{uuid.uuid4()}.png"
        output_path = Path("/tmp") / output_filename
        
        try:
            # Generate image
            result = self._model(
                prompt=prompt,
                negative_prompt=negative_prompt,
                width=width,
                height=height,
                num_inference_steps=20,
                guidance_scale=7.5
            )
            
            # Save image
            result.images[0].save(str(output_path))
            
            return str(output_path)
        except Exception as e:
            raise RuntimeError(f"Image generation failed: {str(e)}")
    
    async def is_available(self) -> bool:
        """
        Check if the image generation service is available.
        
        Returns:
            True if service is available, False otherwise
        """
        return self.model_path.exists()
