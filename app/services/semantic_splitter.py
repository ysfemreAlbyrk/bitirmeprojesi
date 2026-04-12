"""Semantic text splitter for meaningful scene segmentation"""
from typing import List, Dict
import re
from app.providers.llm_provider import LLMProvider


class SemanticSplitter:
    """
    Splits book text into meaningful semantic chunks based on
    scene, atmosphere, and narrative continuity rather than word count.
    """
    
    def __init__(self, llm_provider: LLMProvider):
        self.llm_provider = llm_provider
    
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
