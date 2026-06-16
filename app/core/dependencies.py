"""Dependency injection setup for clean code architecture"""
from fastapi import Depends
from typing import AsyncGenerator

from app.core.database import Database, BookRepository, ChapterRepository, TextChunkRepository, ReadingProgressRepository, UserLibraryRepository
from app.core.storage import StorageService
from app.providers.llm_provider import LLMProvider
from app.providers.audio_provider import AudioGenerationProvider
from app.providers.image_provider import ImageGenerationProvider
from app.providers.gemini_provider import GeminiProvider
from app.providers.stable_audio_provider import StableAudioProvider
from app.providers.local_image_provider import LocalImageProvider
from app.services.audit_service import AuditService
from app.services.semantic_splitter import SemanticSplitter
from app.services.book_processing_service import BookProcessingService


# Singleton instances
_db_instance: Database = None
_llm_provider: LLMProvider = None
_audio_provider: AudioGenerationProvider = None
_image_provider: ImageGenerationProvider = None


def get_database() -> Database:
    """Get or create database singleton instance"""
    global _db_instance
    if _db_instance is None:
        _db_instance = Database()
    return _db_instance


def get_llm_provider() -> LLMProvider:
    """Get or create LLM provider singleton instance based on configuration"""
    global _llm_provider
    if _llm_provider is None:
        from config import settings
        
        if settings.llm_provider == "ollama":
            from app.providers.ollama_provider import OllamaProvider
            _llm_provider = OllamaProvider()
        else:
            _llm_provider = GeminiProvider()
    return _llm_provider


def get_audio_provider() -> AudioGenerationProvider:
    """Get or create audio provider singleton instance"""
    global _audio_provider
    if _audio_provider is None:
        _audio_provider = StableAudioProvider()
    return _audio_provider


def get_image_provider() -> ImageGenerationProvider:
    """Get or create image provider singleton instance based on configuration"""
    global _image_provider
    if _image_provider is None:
        from config import settings
        
        if settings.image_generation_model == "clipdrop":
            from app.providers.clipdrop_provider import ClipdropProvider
            _image_provider = ClipdropProvider()
        else:
            _image_provider = LocalImageProvider()
    return _image_provider


def get_storage_service(
    db: Database = Depends(get_database)
) -> StorageService:
    """Get storage service instance"""
    return StorageService(db.client)


def get_book_repository(
    db: Database = Depends(get_database)
) -> BookRepository:
    """Get book repository instance"""
    return BookRepository(db)


def get_chapter_repository(
    db: Database = Depends(get_database)
) -> ChapterRepository:
    """Get chapter repository instance"""
    return ChapterRepository(db)


def get_text_chunk_repository(
    db: Database = Depends(get_database)
) -> TextChunkRepository:
    """Get text chunk repository instance"""
    return TextChunkRepository(db)


def get_reading_progress_repository(
    db: Database = Depends(get_database)
) -> ReadingProgressRepository:
    """Get reading progress repository instance"""
    return ReadingProgressRepository(db)


def get_user_library_repository(
    db: Database = Depends(get_database)
) -> UserLibraryRepository:
    """Get user library repository instance"""
    return UserLibraryRepository(db)


def get_audit_service(
    llm_provider: LLMProvider = Depends(get_llm_provider)
) -> AuditService:
    """Get audit service instance"""
    return AuditService(llm_provider)


def get_semantic_splitter(
    llm_provider: LLMProvider = Depends(get_llm_provider)
) -> SemanticSplitter:
    """Get semantic splitter instance"""
    return SemanticSplitter(llm_provider)


def get_book_processing_service(
    llm_provider: LLMProvider = Depends(get_llm_provider),
    audio_provider: AudioGenerationProvider = Depends(get_audio_provider),
    image_provider: ImageGenerationProvider = Depends(get_image_provider),
    storage_service: StorageService = Depends(get_storage_service)
) -> BookProcessingService:
    """Get book processing service instance"""
    return BookProcessingService(
        llm_provider,
        audio_provider,
        image_provider,
        storage_service
    )
