"""Clipdrop API implementation of ImageGenerationProvider"""
import httpx
from pathlib import Path
from typing import Optional
from app.providers.image_provider import ImageGenerationProvider
from config import settings


class ClipdropProvider(ImageGenerationProvider):
    """Clipdrop API implementation for image generation"""
    
    def __init__(self):
        self.api_key = settings.clipdrop_api_key
        self.api_url = "https://clipdrop-api.co/text-to-image/v1"
    
    async def generate_image(
        self,
        prompt: str,
        width: int = 512,
        height: int = 512,
        negative_prompt: Optional[str] = None
    ) -> str:
        """
        Generate an image from a text prompt using Clipdrop API.
        
        Args:
            prompt: Text description of the desired image (max 1000 chars)
            width: Image width in pixels (Clipdrop returns 1024x1024)
            height: Image height in pixels (Clipdrop returns 1024x1024)
            negative_prompt: Not supported by Clipdrop API
            
        Returns:
            Path to the generated image file
        """
        # Generate unique output filename
        import uuid
        output_filename = f"image_{uuid.uuid4()}.png"
        output_path = Path("/tmp") / output_filename
        
        # Prepare prompt (Clipdrop max 1000 chars)
        if len(prompt) > 1000:
            prompt = prompt[:1000]
        
        # Prepare request
        headers = {
            "x-api-key": self.api_key
        }
        
        files = {
            "prompt": (None, prompt, "text/plain")
        }
        
        print(f"\n{'='*60}\n[IMAGE PROMPT - Clipdrop]\n{'='*60}\n{prompt[:500]}...\n{'='*60}")
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self.api_url,
                    headers=headers,
                    files=files,
                    timeout=30.0
                )
                
                if response.status_code == 200:
                    # Save image to file
                    with open(output_path, "wb") as f:
                        f.write(response.content)
                    
                    # Log credit usage
                    remaining_credits = response.headers.get("x-remaining-credits", "unknown")
                    credits_consumed = response.headers.get("x-credits-consumed", "unknown")
                    
                    print(f"\n[IMAGE RESPONSE - Clipdrop] Status: 200 OK | Saved to: {output_path} | Credits: {credits_consumed}/{remaining_credits}\n{'='*60}\n")
                    
                    return str(output_path)
                else:
                    error_detail = response.json() if response.headers.get("content-type") == "application/json" else response.text
                    print(f"\n[IMAGE ERROR - Clipdrop] Status: {response.status_code} - {error_detail}\n{'='*60}\n")
                    raise RuntimeError(f"Clipdrop API error: {response.status_code} - {error_detail}")
                    
        except httpx.TimeoutException:
            raise RuntimeError("Clipdrop API request timed out")
        except Exception as e:
            raise RuntimeError(f"Image generation failed: {str(e)}")
    
    def is_available(self) -> bool:
        """
        Check if the Clipdrop API service is available.
        
        Returns:
            True if API key is configured, False otherwise
        """
        return bool(self.api_key)
