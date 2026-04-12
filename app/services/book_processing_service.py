"""Book processing pipeline service"""
import uuid
from pathlib import Path
from typing import Optional
from app.providers.llm_provider import LLMProvider
from app.providers.audio_provider import AudioGenerationProvider
from app.providers.image_provider import ImageGenerationProvider
from app.core.database import BookRepository, ChapterRepository, TextChunkRepository
from app.core.storage import StorageService
from app.services.semantic_splitter import SemanticSplitter
from app.services.audit_service import AuditService
from app.utils.text_extraction import TextExtractor
from app.models.book import ProcessingStatus, AuditResult
from config import settings


class BookProcessingService:
    """
    Orchestrates the entire book processing pipeline:
    1. Text extraction
    2. Audit check
    3. Text segmentation
    4. Scene analysis
    5. Audio generation
    6. Image generation
    7. Database storage
    """
    
    def __init__(
        self,
        llm_provider: LLMProvider,
        audio_provider: AudioGenerationProvider,
        image_provider: ImageGenerationProvider,
        storage_service: StorageService
    ):
        self.llm_provider = llm_provider
        self.audio_provider = audio_provider
        self.image_provider = image_provider
        self.storage_service = storage_service
        
        self.book_repo = BookRepository()
        self.chapter_repo = ChapterRepository()
        self.chunk_repo = TextChunkRepository()
        
        self.semantic_splitter = SemanticSplitter(llm_provider)
        self.audit_service = AuditService(llm_provider)
    
    async def process_book(
        self,
        book_id: str,
        file_path: str,
        file_format: str
    ) -> None:
        """
        Process a book through the entire pipeline.
        
        Args:
            book_id: ID of the book record
            file_path: Path to the book file
            file_format: File format ('epub' or 'pdf')
        """
        # Update status to processing
        self.book_repo.update(book_id, {'processing_status': ProcessingStatus.PROCESSING})
        
        try:
            # Step 1: Extract text
            extracted_data = TextExtractor.extract_text(file_path, file_format)
            full_text = extracted_data['text']
            chapters_data = extracted_data['chapters']
            
            # Step 2: Audit check
            audit_result = await self.audit_service.audit_book(full_text)
            
            if audit_result != AuditResult.APPROVED:
                self.book_repo.update(book_id, {
                    'processing_status': ProcessingStatus.FAILED,
                    'audit_result': audit_result
                })
                return
            
            self.book_repo.update(book_id, {'audit_result': AuditResult.APPROVED})
            
            # Step 3: Create chapters in database
            for chapter_data in chapters_data:
                chapter_record = self.chapter_repo.create({
                    'id': str(uuid.uuid4()),
                    'book_id': book_id,
                    'chapter_number': chapter_data['chapter_number'],
                    'title': chapter_data['title']
                })
                chapter_data['db_id'] = chapter_record['id']
            
            # Step 4: Split text into chunks and process each
            chunks = self.semantic_splitter.split_text(full_text)
            
            for i, chunk_text in enumerate(chunks):
                # Determine which chapter this chunk belongs to
                chapter_id = self._find_chapter_for_chunk(chapters_data, i)
                
                # Create chunk record
                chunk_id = str(uuid.uuid4())
                chunk_record = self.chunk_repo.create({
                    'id': chunk_id,
                    'book_id': book_id,
                    'chapter_id': chapter_id,
                    'order': i,
                    'text': chunk_text,
                    'word_count': len(chunk_text.split()),
                    'analyzed': False
                })
                
                # Step 5: Analyze scene
                analysis = await self.llm_provider.analyze_scene(chunk_text)
                
                # Step 6: Generate audio
                audio_path = await self.audio_provider.generate_audio(
                    prompt=analysis.sfx_prompt,
                    duration=8,
                    negative_prompt="music, speech, noise, distortion"
                )
                audio_url = await self.storage_service.upload_file(audio_path)
                
                # Step 7: Generate image
                image_path = await self.image_provider.generate_image(
                    prompt=analysis.image_prompt,
                    width=512,
                    height=512
                )
                image_url = await self.storage_service.upload_file(image_path)
                
                # Step 8: Update chunk with analysis and media URLs
                self.chunk_repo.update(chunk_id, {
                    'scene': analysis.scene,
                    'emotion': analysis.emotion,
                    'sfx_prompt': analysis.sfx_prompt,
                    'image_prompt': analysis.image_prompt,
                    'audio_url': audio_url,
                    'image_url': image_url,
                    'analyzed': True
                })
            
            # Update book status to completed
            self.book_repo.update(book_id, {'processing_status': ProcessingStatus.COMPLETED})
            
        except Exception as e:
            # Update book status to failed
            self.book_repo.update(book_id, {
                'processing_status': ProcessingStatus.FAILED
            })
            raise e
    
    def _find_chapter_for_chunk(self, chapters_data: list, chunk_index: int) -> str:
        """
        Find which chapter a chunk belongs to based on index.
        Simple implementation - can be enhanced.
        """
        # Distribute chunks evenly across chapters
        total_chunks = len(chapters_data)
        chapter_index = min(chunk_index // (total_chunks + 1), total_chunks - 1)
        return chapters_data[chapter_index]['db_id']
