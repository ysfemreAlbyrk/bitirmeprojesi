"""Book processing service - orchestrates the entire book processing pipeline"""
import uuid
from typing import Optional
from app.models.book import Book, ProcessingStatus, AuditResult
from app.core.database import BookRepository, ChapterRepository, TextChunkRepository, MediaAssetRepository
from app.core.storage import StorageService
from app.utils.text_extraction import TextExtractor
from app.services.audit_service import AuditService
from app.services.semantic_splitter import SemanticSplitter
from app.providers.llm_provider import LLMProvider, SceneAnalysis
from app.providers.audio_provider import AudioGenerationProvider
from app.providers.image_provider import ImageGenerationProvider
from app.core.redis_client import redis_client
from config import settings
from app.utils.logger import get_logger

logger = get_logger("vibetale")


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
        self.media_asset_repo = MediaAssetRepository()
        
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
        logger.info(f"Starting book processing: {book_id}")
        
        # Update status to processing
        self.book_repo.update(book_id, {'processing_status': ProcessingStatus.PROCESSING})
        
        try:
            # Step 1: Extract text
            logger.debug(f"Extracting text from {file_path}")
            extracted_data = TextExtractor.extract_text(file_path, file_format)
            full_text = extracted_data['text']
            chapters_data = extracted_data['chapters']
            total_pages = max(1, len(full_text.split()) // 250)
            logger.info(f"Extracted {len(chapters_data)} chapters, {len(full_text)} characters (~{total_pages} pages)")

            # Persist total_pages early so the frontend can show it immediately
            self.book_repo.update(book_id, {'total_pages': total_pages})
            
            # Step 2: Audit check (skipped on resume if already approved)
            book = self.book_repo.get_by_id(book_id)
            already_approved = bool(book) and book.get('audit_result') == AuditResult.APPROVED.value
            if already_approved:
                logger.info("Audit already approved (resume) - skipping audit")
            else:
                try:
                    redis_val = await redis_client.get("audit_enabled")
                    audit_enabled = redis_val == "true" if redis_val is not None else settings.audit_enabled
                except Exception:
                    audit_enabled = settings.audit_enabled
                if audit_enabled:
                    logger.debug("Performing content audit")
                    audit_result = await self.audit_service.audit_book(full_text)
                    logger.info(f"Audit result: {audit_result}")

                    if audit_result != AuditResult.APPROVED:
                        self.book_repo.update(book_id, {
                            'processing_status': ProcessingStatus.FAILED,
                            'audit_result': audit_result
                        })
                        return
                else:
                    logger.info("Content audit disabled - auto-approving")
                self.book_repo.update(book_id, {'audit_result': AuditResult.APPROVED})

            # Step 2b: Generate cover image (skip if already present on resume)
            if not book.get('cover_url'):
                try:
                    book_title = book.get('title', 'Book')
                    book_author = book.get('author', '')
                    cover_prompt = f"Beautiful book cover illustration for '{book_title}' by {book_author}, cinematic lighting, artistic, detailed"
                    cover_path = await self.image_provider.generate_image(
                        prompt=cover_prompt, width=512, height=768
                    )
                    cover_url = await self.storage_service.upload_file(cover_path)
                    self.book_repo.update(book_id, {'cover_url': cover_url})
                    logger.info(f"Cover generated for book {book_id}")
                except Exception as cover_err:
                    logger.warning(f"Cover generation failed (non-critical): {cover_err}")
            else:
                logger.info("Cover already exists (resume) - skipping")

            # Step 3: Chapters (reuse existing on resume, otherwise create)
            existing_chapters = self.chapter_repo.get_by_book(book_id) or []
            chapter_id_by_number = {}
            if existing_chapters:
                logger.info(f"Reusing {len(existing_chapters)} existing chapter records")
                for ch in existing_chapters:
                    chapter_id_by_number[ch['chapter_number']] = ch['id']
            else:
                logger.debug(f"Creating {len(chapters_data)} chapter records")
                for chapter_data in chapters_data:
                    chapter_record = self.chapter_repo.create({
                        'id': str(uuid.uuid4()),
                        'book_id': book_id,
                        'chapter_number': chapter_data['chapter_number'],
                        'title': chapter_data['title']
                    })
                    chapter_id_by_number[chapter_data['chapter_number']] = chapter_record['id']

            # Step 4: Chunks (resume from stored chunks, or semantic-split per chapter)
            chunk_records = self.chunk_repo.get_by_book(book_id) or []
            if chunk_records:
                chunk_records = sorted(chunk_records, key=lambda c: c.get('order', 0))
                logger.info(f"Resuming with {len(chunk_records)} existing chunks")
            else:
                logger.debug("Splitting each chapter into semantic chunks")
                order = 0
                for chapter_data in chapters_data:
                    chapter_id = chapter_id_by_number.get(chapter_data['chapter_number'])
                    scene_chunks = await self.semantic_splitter.split_semantic(chapter_data['text'])
                    for chunk_text in scene_chunks:
                        record = self.chunk_repo.create({
                            'id': str(uuid.uuid4()),
                            'book_id': book_id,
                            'chapter_id': chapter_id,
                            'order': order,
                            'text': chunk_text,
                            'word_count': len(chunk_text.split()),
                            'analyzed': False
                        })
                        chunk_records.append(record)
                        order += 1
                logger.info(f"Created {len(chunk_records)} chunks across {len(chapters_data)} chapters")

            # Step 5: Process each chunk (analyze + media), skipping completed work
            for i, chunk in enumerate(chunk_records):
                logger.debug(f"Processing chunk {i + 1}/{len(chunk_records)}")
                await self._process_chunk(chunk)

            # Update book status to completed
            self.book_repo.update(book_id, {'processing_status': ProcessingStatus.COMPLETED})

        except Exception as e:
            # Update book status to failed
            self.book_repo.update(book_id, {
                'processing_status': ProcessingStatus.FAILED
            })
            raise e

    async def _process_chunk(self, chunk: dict) -> None:
        """
        Analyze a single chunk and generate its media, resuming safely:
        - reuses a cached analysis when the chunk is already analyzed
        - only generates audio/image that are still missing
        """
        chunk_id = chunk['id']
        text = chunk['text']

        # Step 5a: Scene analysis (cached if already analyzed)
        if chunk.get('analyzed'):
            analysis = SceneAnalysis(
                scene=chunk.get('scene') or "",
                emotion=chunk.get('emotion') or "",
                sfx_prompt=chunk.get('sfx_prompt') or "",
                image_prompt=chunk.get('image_prompt') or ""
            )
        else:
            analysis = await self.llm_provider.analyze_scene(text)
            self.chunk_repo.update(chunk_id, {
                'scene': analysis.scene,
                'emotion': analysis.emotion,
                'sfx_prompt': analysis.sfx_prompt,
                'image_prompt': analysis.image_prompt,
                'analyzed': True
            })

        # Step 5b: Generate audio only if needed and not already present
        if analysis.sfx_prompt and not chunk.get('audio_url'):
            audio_path = await self.audio_provider.generate_audio(
                prompt=analysis.sfx_prompt,
                duration=8,
                negative_prompt="music, speech, noise, distortion"
            )
            audio_url = await self.storage_service.upload_file(audio_path)
            self.chunk_repo.update(chunk_id, {'audio_url': audio_url})
            self.media_asset_repo.create({
                'id': str(uuid.uuid4()),
                'chunk_id': chunk_id,
                'asset_type': 'audio',
                'storage_url': audio_url
            })

        # Step 5c: Generate image only if needed and not already present
        if analysis.image_prompt and not chunk.get('image_url'):
            image_path = await self.image_provider.generate_image(
                prompt=analysis.image_prompt,
                width=512,
                height=512
            )
            image_url = await self.storage_service.upload_file(image_path)
            self.chunk_repo.update(chunk_id, {'image_url': image_url})
            self.media_asset_repo.create({
                'id': str(uuid.uuid4()),
                'chunk_id': chunk_id,
                'asset_type': 'image',
                'storage_url': image_url
            })
