"""Ollama implementation of LLMProvider"""
import httpx
from typing import Dict, Any
from app.providers.llm_provider import LLMProvider, SceneAnalysis
from config import settings


class OllamaProvider(LLMProvider):
    """Ollama local model implementation for text analysis"""
    
    def __init__(self):
        self.base_url = settings.ollama_base_url or "http://localhost:11434"
        self.model = settings.ollama_model or "llama2"
    
    async def _call_ollama(self, prompt: str) -> str:
        """
        Make a call to Ollama API.
        
        Args:
            prompt: The prompt to send to the model
            
        Returns:
            The model's response text
        """
        url = f"{self.base_url}/api/generate"
        
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": 0.7,
                "top_p": 0.9
            }
        }
        
        print(f"\n{'='*60}\n[LLM PROMPT - Ollama]\n{'='*60}\n{prompt[:500]}...\n{'='*60}")
        
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(url, json=payload)
                response.raise_for_status()
                result = response.json()
                response_text = result.get("response", "")
                print(f"\n[LLM RESPONSE - Ollama]\n{'-'*60}\n{response_text[:500]}...\n{'='*60}\n")
                return response_text
        except httpx.TimeoutException:
            raise RuntimeError("Ollama request timed out")
        except Exception as e:
            print(f"\n[LLM ERROR - Ollama] {str(e)}\n{'='*60}\n")
            raise RuntimeError(f"Ollama API error: {str(e)}")
    
    async def analyze_scene(self, text: str) -> SceneAnalysis:
        """
        Analyze a text segment and extract scene information.
        
        Args:
            text: The text segment to analyze
            
        Returns:
            SceneAnalysis containing scene description, emotion, and prompts
        """
        system_prompt = """You are analyzing a text segment from a book to generate 
        ambient audio and visual content. Extract the following in JSON format:
        
        {
            "scene": "brief English description of the scene (e.g., 'dark forest at night', 'medieval tavern')",
            "emotion": "emotional tone of the scene (e.g., 'tense, mysterious', 'warm, cozy')",
            "sfx_prompt": "prompt for ambient sound generation - ONLY include nature sounds, ambient noises, and physical sounds. DO NOT include music, speech, or specific mechanical sounds",
            "image_prompt": "detailed prompt for scene visual generation"
        }
        
        IMPORTANT: For sfx_prompt, focus on: wind, rain, birds, ocean waves, fire crackling, footsteps, ambient room noise, etc."""
        
        full_prompt = f"{system_prompt}\n\nText segment:\n{text}"
        
        try:
            response_text = await self._call_ollama(full_prompt)
            
            # Try to extract JSON from response
            import json
            import re
            
            # Look for JSON pattern in response
            json_match = re.search(r'\{[^{}]*\}', response_text, re.DOTALL)
            if json_match:
                result = json.loads(json_match.group())
            else:
                # Fallback: try to parse entire response as JSON
                result = json.loads(response_text)
            
            return SceneAnalysis(
                scene=result.get("scene", "generic scene"),
                emotion=result.get("emotion", "neutral"),
                sfx_prompt=result.get("sfx_prompt", "ambient background"),
                image_prompt=result.get("image_prompt", "generic background")
            )
        except Exception as e:
            # Return default values on error
            return SceneAnalysis(
                scene="generic scene",
                emotion="neutral",
                sfx_prompt="ambient background",
                image_prompt="generic background"
            )
    
    async def check_copyright(self, text: str) -> Dict[str, Any]:
        """
        Check if the text has copyright issues.
        
        Args:
            text: The text to check
            
        Returns:
            Dict with copyright analysis result
        """
        prompt = f"""Analyze the following text for copyright concerns.
        Determine if this appears to be:
        1. Public domain content
        2. Content that might have copyright restrictions
        3. Clearly copyrighted material
        
        Return JSON with:
        {{
            "status": "approved" | "suspicious" | "violation",
            "reason": "brief explanation",
            "confidence": 0.0-1.0
        }}
        
        Text:\n{text}"""
        
        try:
            response_text = await self._call_ollama(prompt)
            import json
            import re
            
            json_match = re.search(r'\{[^{}]*\}', response_text, re.DOTALL)
            if json_match:
                result = json.loads(json_match.group())
            else:
                result = json.loads(response_text)
            
            return result
        except Exception as e:
            return {"status": "audit_failed", "reason": str(e), "confidence": 0.0}
    
    async def check_ethics(self, text: str) -> Dict[str, Any]:
        """
        Check if the text contains unethical content.
        
        Args:
            text: The text to check
            
        Returns:
            Dict with ethics analysis result
        """
        prompt = f"""Analyze the following text for ethical concerns.
        Check for: hate speech, excessive violence, explicit content, or other inappropriate material.
        
        Return JSON with:
        {{
            "status": "approved" | "violation",
            "reason": "brief explanation",
            "categories": ["list of any flagged categories"],
            "confidence": 0.0-1.0
        }}
        
        Text:\n{text}"""
        
        try:
            response_text = await self._call_ollama(prompt)
            import json
            import re
            
            json_match = re.search(r'\{[^{}]*\}', response_text, re.DOTALL)
            if json_match:
                result = json.loads(json_match.group())
            else:
                result = json.loads(response_text)
            
            return result
        except Exception as e:
            return {"status": "audit_failed", "reason": str(e), "confidence": 0.0}
    
    def is_available(self) -> bool:
        """
        Check if Ollama service is available.
        
        Returns:
            True if service is available, False otherwise
        """
        try:
            url = f"{self.base_url}/api/tags"
            import httpx
            with httpx.Client(timeout=5.0) as client:
                response = client.get(url)
                return response.status_code == 200
        except Exception:
            return False
