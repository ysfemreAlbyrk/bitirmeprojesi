"""Semantic text splitter for meaningful scene segmentation"""
from typing import List, Dict, Optional
import re
from app.providers.llm_provider import LLMProvider
from app.utils.logger import get_logger

logger = get_logger("vibetale")

# How many paragraphs to send to the LLM per boundary-detection call.
# Lower value = shorter prompts (safer for 500 errors), more API calls.
_BOUNDARY_WINDOW = 20


class SemanticSplitter:
    """
    Splits book text into meaningful semantic chunks based on
    scene, atmosphere, and narrative continuity rather than word count.
    """
    
    def __init__(self, llm_provider: Optional[LLMProvider] = None):
        self.llm_provider = llm_provider

    # ── Semantic (LLM-based) splitting ──────────────────────────────────────

    async def split_semantic(
        self,
        text: str,
        target_chunk_size: int = 400,
        max_chunk_size: int = 900,
        min_chunk_size: int = 80,
    ) -> List[str]:
        """
        Split text into semantically coherent scene chunks using the LLM to
        detect scene boundaries between paragraphs. Falls back to rule-based
        splitting when no LLM is configured or detection fails.

        The original text is preserved verbatim: the LLM only returns boundary
        indices, never rewritten content.
        """
        text = (text or "").strip()
        if not text:
            return []

        paragraphs = self._split_into_paragraphs(text)

        # Not enough structure to segment semantically -> rule-based
        if self.llm_provider is None or len(paragraphs) < 2:
            return self.split_text(text, target_chunk_size, max_chunk_size)

        try:
            boundaries = await self._detect_boundaries_windowed(paragraphs)
        except Exception as e:
            logger.warning(f"Semantic boundary detection failed, falling back: {e}")
            boundaries = []

        if not boundaries:
            return self.split_text(text, target_chunk_size, max_chunk_size)

        scenes = self._group_by_boundaries(paragraphs, boundaries)
        return self._enforce_size_limits(scenes, max_chunk_size, min_chunk_size)

    async def _detect_boundaries_windowed(self, paragraphs: List[str]) -> List[int]:
        """Run boundary detection in windows to bound prompt size, then merge
        the per-window indices back into the global paragraph space."""
        all_boundaries: List[int] = []
        for start in range(0, len(paragraphs), _BOUNDARY_WINDOW):
            window = paragraphs[start:start + _BOUNDARY_WINDOW]
            local = await self.llm_provider.detect_scene_boundaries(window)
            for idx in local:
                global_idx = start + idx
                if 0 < global_idx < len(paragraphs):
                    all_boundaries.append(global_idx)
            # Window edges are natural boundaries between separate calls
            if start > 0:
                all_boundaries.append(start)
        return sorted(set(all_boundaries))

    def _group_by_boundaries(self, paragraphs: List[str], boundaries: List[int]) -> List[str]:
        """Join paragraphs into scene chunks using the boundary start indices."""
        starts = [0] + [b for b in boundaries if 0 < b < len(paragraphs)]
        starts = sorted(set(starts))
        starts.append(len(paragraphs))

        scenes: List[str] = []
        for i in range(len(starts) - 1):
            scene_paras = paragraphs[starts[i]:starts[i + 1]]
            scene = "\n\n".join(scene_paras).strip()
            if scene:
                scenes.append(scene)
        return scenes

    def _enforce_size_limits(
        self,
        scenes: List[str],
        max_chunk_size: int,
        min_chunk_size: int,
    ) -> List[str]:
        """Sub-split scenes that are too large and merge scenes that are too
        small into their neighbour, keeping chunks within reasonable bounds."""
        # Sub-split oversized scenes with the rule-based splitter
        sized: List[str] = []
        for scene in scenes:
            if len(scene.split()) > max_chunk_size:
                sized.extend(self.split_text(scene, max_chunk_size // 2, max_chunk_size))
            else:
                sized.append(scene)

        # Merge undersized chunks forward
        merged: List[str] = []
        for chunk in sized:
            if merged and len(chunk.split()) < min_chunk_size:
                merged[-1] = merged[-1] + "\n\n" + chunk
            else:
                merged.append(chunk)
        return merged

    def _split_into_paragraphs(self, text: str) -> List[str]:
        """Split text into paragraphs on blank lines, with a sentence-based
        fallback when the text has no paragraph breaks."""
        paragraphs = [p.strip() for p in re.split(r'\n\s*\n', text) if p.strip()]
        if len(paragraphs) >= 2:
            return paragraphs
        # No paragraph structure: group sentences into pseudo-paragraphs
        sentences = self._split_into_sentences(text)
        pseudo: List[str] = []
        for i in range(0, len(sentences), 3):
            pseudo.append(" ".join(sentences[i:i + 3]))
        return pseudo or [text]

    # ── Rule-based splitting (fallback / deterministic) ─────────────────────
    
    def split_text(
        self,
        text: str,
        target_chunk_size: int = 500,
        max_chunk_size: int = 1000
    ) -> List[str]:
        """
        Split text into semantic chunks.
        
        Args:
            text: Full text to split
            target_chunk_size: Target words per chunk
            max_chunk_size: Maximum words per chunk
            
        Returns:
            List of text chunks
        """
        # First, split into sentences
        sentences = self._split_into_sentences(text)
        
        chunks = []
        current_chunk = []
        current_word_count = 0
        
        for sentence in sentences:
            sentence_words = len(sentence.split())
            
            # Check if adding this sentence would exceed max size
            if current_word_count + sentence_words > max_chunk_size and current_chunk:
                chunks.append(" ".join(current_chunk))
                current_chunk = []
                current_word_count = 0
            
            # Add sentence to current chunk
            current_chunk.append(sentence)
            current_word_count += sentence_words
            
            # Check if we've reached target size and this is a good break point
            if current_word_count >= target_chunk_size:
                if self._is_good_break_point(sentence):
                    chunks.append(" ".join(current_chunk))
                    current_chunk = []
                    current_word_count = 0
        
        # Add remaining text
        if current_chunk:
            chunks.append(" ".join(current_chunk))
        
        return chunks
    
    def _split_into_sentences(self, text: str) -> List[str]:
        """Split text into sentences using regex"""
        # Simple sentence splitting - can be enhanced with NLP
        sentences = re.split(r'(?<=[.!?])\s+', text)
        return [s.strip() for s in sentences if s.strip()]
    
    def _is_good_break_point(self, sentence: str) -> bool:
        """
        Determine if a sentence is a good break point for chunking.
        Good break points are scene transitions, paragraph endings, etc.
        """
        # Check for scene transition indicators
        transition_indicators = [
            'chapter', 'meanwhile', 'later', 'suddenly', 
            'however', 'meanwhile', 'elsewhere'
        ]
        
        sentence_lower = sentence.lower()
        
        # Check if sentence starts with transition indicator
        for indicator in transition_indicators:
            if sentence_lower.startswith(indicator):
                return True
        
        # Check for paragraph-like endings
        if sentence.endswith(('.', '!', '?')):
            return True
        
        return False
    
    async def split_with_analysis(
        self,
        text: str,
        target_chunk_size: int = 500
    ) -> List[Dict]:
        """
        Split text and perform LLM analysis on each chunk.
        
        Args:
            text: Full text to split
            target_chunk_size: Target words per chunk
            
        Returns:
            List of chunks with analysis results
        """
        chunks = self.split_text(text, target_chunk_size)
        
        analyzed_chunks = []
        for i, chunk in enumerate(chunks):
            try:
                analysis = await self.llm_provider.analyze_scene(chunk)
                analyzed_chunks.append({
                    'text': chunk,
                    'order': i,
                    'word_count': len(chunk.split()),
                    'scene': analysis.scene,
                    'emotion': analysis.emotion,
                    'sfx_prompt': analysis.sfx_prompt,
                    'image_prompt': analysis.image_prompt
                })
            except Exception as e:
                # Fallback if analysis fails
                analyzed_chunks.append({
                    'text': chunk,
                    'order': i,
                    'word_count': len(chunk.split()),
                    'scene': 'generic scene',
                    'emotion': 'neutral',
                    'sfx_prompt': 'ambient background',
                    'image_prompt': 'generic background'
                })
        
        return analyzed_chunks
