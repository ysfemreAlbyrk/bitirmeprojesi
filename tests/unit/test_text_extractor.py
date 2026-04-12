"""Unit tests for TextExtractor"""
import pytest
from pathlib import Path
from app.utils.text_extraction import TextExtractor


@pytest.mark.unit
class TestTextExtractor:
    """Test cases for TextExtractor"""
    
    @pytest.fixture
    def extractor(self):
        """Create TextExtractor instance"""
        return TextExtractor()
    
    def test_extract_text_unsupported_format(self, extractor):
        """Test extracting text from unsupported format"""
        with pytest.raises(ValueError):
            extractor.extract_text("test.txt", "txt")
    
    def test_extract_text_nonexistent_file(self, extractor):
        """Test extracting text from non-existent file"""
        with pytest.raises(FileNotFoundError):
            extractor.extract_text("/nonexistent/file.epub", "epub")
    
    @pytest.mark.asyncio
    async def test_extract_text_epub_basic(self, extractor, tmp_path):
        """Test basic EPUB text extraction structure"""
        # This test would require a real EPUB file
        # For now, we test the error handling
        with pytest.raises(FileNotFoundError):
            await extractor.extract_text(str(tmp_path / "test.epub"), "epub")
    
    @pytest.mark.asyncio
    async def test_extract_text_pdf_basic(self, extractor, tmp_path):
        """Test basic PDF text extraction structure"""
        # This test would require a real PDF file
        # For now, we test the error handling
        with pytest.raises(FileNotFoundError):
            await extractor.extract_text(str(tmp_path / "test.pdf"), "pdf")
