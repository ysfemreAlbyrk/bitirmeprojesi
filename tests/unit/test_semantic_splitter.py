"""Unit tests for SemanticSplitter"""
import pytest
from app.services.semantic_splitter import SemanticSplitter


@pytest.mark.unit
class TestSemanticSplitter:
    """Test cases for SemanticSplitter service"""
    
    @pytest.fixture
    def splitter(self):
        """Create SemanticSplitter instance"""
        return SemanticSplitter()
    
    @pytest.fixture
    def sample_text(self):
        """Sample text for testing"""
        return """
        Chapter 1: The Beginning
        
        The morning sun cast long shadows across the dusty road. John walked slowly, 
        enjoying the quiet countryside. Birds sang in the trees above him.
        
        Suddenly, a loud noise broke the silence. John stopped and looked around. 
        A dark figure appeared in the distance, moving quickly towards him.
        
        The figure drew closer, revealing itself to be Mary, his old friend.
        "John!" she called out, waving her hand. "I've been looking for you everywhere."
        
        John smiled, relieved. "Mary! What brings you here?"
        
        "I have important news," she said, her face serious.
        """
    
    def test_split_text_basic(self, splitter, sample_text):
        """Test basic rule-based text splitting"""
        chunks = splitter.split_text(sample_text)

        assert isinstance(chunks, list)
        assert len(chunks) > 0
        assert all(isinstance(chunk, str) for chunk in chunks)
        assert all(len(chunk.strip()) > 0 for chunk in chunks)

    def test_split_text_word_limit(self, splitter):
        """Chunks should not exceed max_chunk_size in words."""
        text = " ".join(f"word{i}." for i in range(300))
        chunks = splitter.split_text(text, target_chunk_size=20, max_chunk_size=50)
        assert all(len(chunk.split()) <= 50 for chunk in chunks)

    def test_split_empty_text(self, splitter):
        """Test splitting empty text"""
        assert splitter.split_text("") == []

    def test_split_single_chunk(self, splitter):
        """Test splitting text that fits in one chunk"""
        short_text = "This is a short text."
        chunks = splitter.split_text(short_text, max_chunk_size=1000)

        assert len(chunks) == 1
        assert chunks[0] == short_text.strip()

    @pytest.mark.asyncio
    async def test_split_semantic_uses_boundaries(self, mock_llm_provider):
        """split_semantic should group paragraphs at the detected boundaries."""
        mock_llm_provider.detect_scene_boundaries.return_value = [2]
        splitter = SemanticSplitter(mock_llm_provider)
        text = "Para one.\n\nPara two.\n\nPara three.\n\nPara four."

        chunks = await splitter.split_semantic(text, min_chunk_size=0)

        assert len(chunks) == 2
        assert "Para one." in chunks[0] and "Para two." in chunks[0]
        assert "Para three." in chunks[1] and "Para four." in chunks[1]

    @pytest.mark.asyncio
    async def test_split_semantic_fallback_without_llm(self):
        """Without an LLM, split_semantic falls back to rule-based splitting."""
        splitter = SemanticSplitter()
        text = "One sentence here.\n\nAnother sentence there."
        chunks = await splitter.split_semantic(text)
        assert len(chunks) >= 1
        assert all(isinstance(c, str) for c in chunks)

    @pytest.mark.asyncio
    async def test_split_semantic_fallback_when_no_boundaries(self, mock_llm_provider):
        """Empty boundary detection falls back to rule-based splitting."""
        mock_llm_provider.detect_scene_boundaries.return_value = []
        splitter = SemanticSplitter(mock_llm_provider)
        text = "Para one.\n\nPara two.\n\nPara three."
        chunks = await splitter.split_semantic(text)
        assert len(chunks) >= 1
