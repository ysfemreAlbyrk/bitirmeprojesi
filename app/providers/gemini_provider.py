"""Gemini API implementation of LLMProvider"""
import json
import re
import time
from typing import Dict, Any, Callable, TypeVar
from google import genai
from app.providers.llm_provider import LLMProvider, SceneAnalysis
from app.utils.api_logger import ApiCallTimer, log_api_request
from config import settings


T = TypeVar("T")


def _with_retry(
    fn: Callable[[], T],
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 30.0,
    on_retry_msg: str = "LLM call",
) -> T:
    """Call fn with exponential backoff on failure."""
    for attempt in range(1, max_retries + 1):
        try:
            return fn()
        except Exception as e:
            if attempt == max_retries:
                raise
            delay = min(base_delay * (2 ** (attempt - 1)), max_delay)
            print(f"\n[LLM RETRY - {on_retry_msg}] Attempt {attempt}/{max_retries} failed: {e}. Retrying in {delay}s…")
            time.sleep(delay)
    # Should never reach here
    raise RuntimeError("Unexpected end of retry loop")


def _extract_json(text: str) -> dict:
    """Extract JSON from text that may be wrapped in markdown code blocks."""
    text = text.strip()
    # Remove markdown code block markers
    if text.startswith("```json"):
        text = text[7:]
    elif text.startswith("```"):
        text = text[3:]
    if text.endswith("```"):
        text = text[:-3]
    text = text.strip()
    return json.loads(text)


class GeminiProvider(LLMProvider):
    """Gemini API implementation for text analysis"""
    
    def __init__(self):
        self.client = genai.Client(api_key=settings.gemini_api_key)
        self.model_name = settings.gemini_model
    
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
            "sfx_prompt": "prompt for ambient sound generation - ONLY include nature sounds, ambient noises, and physical sounds. DO NOT include music, speech, or specific mechanical sounds that MMAudio cannot handle well",
            "image_prompt": "detailed prompt for scene visual generation"
        }

        IMPORTANT: For sfx_prompt, MMAudio has limitations:
        - Does NOT handle human speech well
        - NOT trained for music generation
        May not recognize very specific mechanical sounds
        - Focus on: wind, rain, birds, ocean waves, fire crackling, footsteps, ambient room noise, etc.
        """

        full_prompt = f"{system_prompt}\n\nText segment:\n{text}"

        print(f"\n{'='*60}\n[LLM PROMPT - analyze_scene]\n{'='*60}\n{full_prompt[:500]}...\n{'='*60}")

        try:
            with ApiCallTimer("Gemini", "analyze_scene", f"model={self.model_name}") as timer:
                def _call():
                    return self.client.models.generate_content(
                        model=self.model_name,
                        contents=full_prompt
                    )

                response = _with_retry(_call, on_retry_msg="analyze_scene")
                timer.status = "200 OK"
            result_text = response.text

            print(f"\n[LLM RESPONSE - analyze_scene]\n{'-'*60}\n{result_text[:500]}...\n{'='*60}\n")

            # Parse JSON response (handle markdown code blocks)
            result = _extract_json(result_text)

            return SceneAnalysis(
                scene=result.get("scene", ""),
                emotion=result.get("emotion", ""),
                sfx_prompt=result.get("sfx_prompt", ""),
                image_prompt=result.get("image_prompt", "")
            )
        except Exception as e:
            print(f"\n[LLM ERROR - analyze_scene] {str(e)}\n{'='*60}\n")
            # Return default values on error
            return SceneAnalysis(
                scene="generic scene",
                emotion="neutral",
                sfx_prompt="ambient background noise",
                image_prompt="generic background scene"
            )
    
    def is_available(self) -> bool:
        """Check if Gemini API is available and configured."""
        try:
            with ApiCallTimer("Gemini", "is_available", "models.list") as timer:
                self.client.models.list()
                timer.status = "200 OK"
            return True
        except Exception:
            return False
    
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

        print(f"\n{'='*60}\n[LLM PROMPT - check_copyright]\n{'='*60}\n{prompt[:500]}...\n{'='*60}")

        try:
            with ApiCallTimer("Gemini", "check_copyright", f"model={self.model_name}") as timer:
                def _call():
                    return self.client.models.generate_content(
                        model=self.model_name,
                        contents=prompt
                    )

                response = _with_retry(_call, on_retry_msg="check_copyright")
                timer.status = "200 OK"
            print(f"\n[LLM RESPONSE - check_copyright]\n{'-'*60}\n{response.text[:500]}...\n{'='*60}\n")
            result = _extract_json(response.text)
            return result
        except Exception as e:
            print(f"\n[LLM ERROR - check_copyright] {str(e)}\n{'='*60}\n")
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

        print(f"\n{'='*60}\n[LLM PROMPT - check_ethics]\n{'='*60}\n{prompt[:500]}...\n{'='*60}")

        try:
            with ApiCallTimer("Gemini", "check_ethics", f"model={self.model_name}") as timer:
                def _call():
                    return self.client.models.generate_content(
                        model=self.model_name,
                        contents=prompt
                    )

                response = _with_retry(_call, on_retry_msg="check_ethics")
                timer.status = "200 OK"
            print(f"\n[LLM RESPONSE - check_ethics]\n{'-'*60}\n{response.text[:500]}...\n{'='*60}\n")
            result = _extract_json(response.text)
            return result
        except Exception as e:
            print(f"\n[LLM ERROR - check_ethics] {str(e)}\n{'='*60}\n")
            return {"status": "audit_failed", "reason": str(e), "confidence": 0.0}
