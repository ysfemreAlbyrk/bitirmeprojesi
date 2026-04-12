"""Text extraction utilities for EPUB and PDF files"""
from pathlib import Path
from typing import Optional
import ebooklib
from ebooklib import epub
from pypdf import PdfReader


class TextExtractor:
    """Utility class for extracting text from EPUB and PDF files"""
    
    @staticmethod
    def extract_from_epub(file_path: str) -> dict:
        """
        Extract text and chapter structure from EPUB file.
        
        Args:
            file_path: Path to the EPUB file
            
        Returns:
            Dict with 'text' (full text) and 'chapters' (list of chapter info)
        """
        book = epub.read_epub(file_path)
        
        # Extract full text
        full_text = ""
        chapters = []
        chapter_num = 0
        
        for item in book.get_items():
            if item.get_type() == ebooklib.ITEM_DOCUMENT:
                content = item.get_content()
                # Parse HTML content
                from bs4 import BeautifulSoup
                soup = BeautifulSoup(content, 'html.parser')
                text = soup.get_text()
                
                if text.strip():
                    chapter_num += 1
                    chapter_title = item.get_name()
                    
                    chapters.append({
                        'chapter_number': chapter_num,
                        'title': chapter_title,
                        'text': text
                    })
                    full_text += text + "\n\n"
        
        return {
            'text': full_text,
            'chapters': chapters
        }
    
    @staticmethod
    def extract_from_pdf(file_path: str) -> dict:
        """
        Extract text from PDF file.
        
        Args:
            file_path: Path to the PDF file
            
        Returns:
            Dict with 'text' (full text) and 'chapters' (list of page-based chapters)
        """
        reader = PdfReader(file_path)
        full_text = ""
        chapters = []
        
        for page_num, page in enumerate(reader.pages, 1):
            text = page.extract_text()
            if text.strip():
                chapters.append({
                    'chapter_number': page_num,
                    'title': f"Page {page_num}",
                    'text': text
                })
                full_text += text + "\n\n"
        
        return {
            'text': full_text,
            'chapters': chapters
        }
    
    @staticmethod
    def extract_text(file_path: str, file_format: str) -> dict:
        """
        Extract text from file based on format.
        
        Args:
            file_path: Path to the file
            file_format: File format ('epub' or 'pdf')
            
        Returns:
            Dict with 'text' and 'chapters'
        """
        if file_format.lower() == 'epub':
            return TextExtractor.extract_from_epub(file_path)
        elif file_format.lower() == 'pdf':
            return TextExtractor.extract_from_pdf(file_path)
        else:
            raise ValueError(f"Unsupported file format: {file_format}")
