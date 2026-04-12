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
        """Test basic text splitting"""
        chunks = splitter.split_text(sample_text)
        
        assert isinstance(chunks, list)
        assert len(chunks) > 0
        assert all(isinstance(chunk, str) for chunk in chunks)
        assert all(len(chunk.strip()) > 0 for chunk in chunks)
    
    def test_split_text_with_chunk_size(self, splitter, sample_text):
        """Test text splitting with chunk size limit"""
        chunks = splitter.split_text(sample_text, max_chunk_size=100)
        
        assert all(len(chunk) <= 100 for chunk in chunks)
    
    @pytest.mark.asyncio
    async def test_split_text_with_analysis(self, splitter, sample_text, mock_llm_provider):
        """Test text splitting with LLM analysis"""
        chunks = await splitter.split_text(sample_text, llm_provider=mock_llm_provider, analyze=True)
        
        assert len(chunks) > 0
        assert hasattr(chunks[0], 'text')
        assert hasattr(chunks[0], 'scene')
        assert hasattr(chunks[0], 'emotion')
    
    def test_split_empty_text(self, splitter):
        """Test splitting empty text"""
        chunks = splitter.split_text("")
        
        assert chunks == []
    
    def test_split_single_chunk(self, splitter):
        """Test splitting text that fits in one chunk"""
        short_text = "This is a short text."
        chunks = splitter.split_text(short_text, max_chunk_size=1000)
        
        assert len(chunks) == 1
        assert chunks[0] == short_text.strip()
