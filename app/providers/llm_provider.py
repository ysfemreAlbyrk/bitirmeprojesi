"""LLM Provider abstraction for text analysis"""
from abc import ABC, abstractmethod
from typing import Dict, Any, List
from dataclasses import dataclass


@dataclass
class SceneAnalysis:
    """Result of scene analysis"""
    scene: str
    emotion: str
    sfx_prompt: str
    image_prompt: str


class LLMProvider(ABC):
    """Abstract base class for LLM providers"""
    
    @abstractmethod
    async def analyze_scene(self, text: str) -> SceneAnalysis:
        """
        Analyze a text segment and extract scene information.
        
        Args:
            text: The text segment to analyze
            
        Returns:
            SceneAnalysis containing scene description, emotion, and prompts
        """
        pass
    
    @abstractmethod
    async def check_copyright(self, text: str) -> Dict[str, Any]:
        """
        Check if the text has copyright issues.
        
        Args:
            text: The text to check
            
        Returns:
            Dict with copyright analysis result
        """
        pass
    
    @abstractmethod
    async def check_ethics(self, text: str) -> Dict[str, Any]:
        """
        Check if the text contains unethical content.
        
        Args:
            text: The text to check
            
        Returns:
            Dict with ethics analysis result
        """
        pass
    
    async def detect_scene_boundaries(self, paragraphs: List[str]) -> List[int]:
        """
        Detect semantic scene boundaries across a list of paragraphs.

        A boundary marks the index of a paragraph where a NEW scene begins
        (change of location, time, mood, or narrative event). Index 0 is an
        implicit boundary and need not be returned.

        Args:
            paragraphs: Ordered paragraphs of a chapter/section

        Returns:
            Sorted list of paragraph indices (1-based positions within the list)
            where a new scene starts. An empty list means "no semantic split
            available" and callers should fall back to rule-based splitting.
        """
        return []

    @abstractmethod
    def is_available(self) -> bool:
        """Check if the provider is available and configured."""
        pass
