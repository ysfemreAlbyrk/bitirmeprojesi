"""Celery tasks for book processing"""
import asyncio
from celery import shared_task
from app.services.book_processing_service import BookProcessingService
from app.core.dependencies import (
    get_database,
    get_llm_provider,
    get_audio_provider,
    get_image_provider
)
from app.core.storage import StorageService
from app.utils.logger import get_logger

logger = get_logger("vibetale")


@shared_task(bind=True, name="process_book_async")
def process_book_async(self, book_id: str, file_path: str, file_format: str):
    """
    Async task for processing a book.
    
    Args:
        book_id: ID of the book record
        file_path: Path to the book file
        file_format: File format ('epub' or 'pdf')
    """
    logger.info(f"Starting async book processing for book_id: {book_id}")
    
    try:
        # Manually instantiate providers and services (no FastAPI Depends() in Celery context)
        db = get_database()
        llm = get_llm_provider()
        audio = get_audio_provider()
        image = get_image_provider()
        storage = StorageService(db.client)
        
        processing_service = BookProcessingService(
            llm_provider=llm,
            audio_provider=audio,
            image_provider=image,
            storage_service=storage
        )
        
        # Process the book (async method wrapped for sync Celery context)
        asyncio.run(processing_service.process_book(
            book_id=book_id,
            file_path=file_path,
            file_format=file_format
        ))
        
        logger.info(f"Book processing completed successfully: {book_id}")
        return {"status": "completed", "book_id": book_id}
        
    except Exception as e:
        logger.error(f"Book processing failed for book_id {book_id}: {str(e)}", exc_info=True)
        self.retry(exc=e, countdown=60, max_retries=3)
        return {"status": "failed", "book_id": book_id, "error": str(e)}
    finally:
        # Clean up temp file after processing
        from pathlib import Path
        tmp = Path(file_path)
        if tmp.exists():
            tmp.unlink()
            logger.debug(f"Cleaned up temp file: {file_path}")


@shared_task(name="cleanup_temp_files")
def cleanup_temp_files():
    """
    Background task to clean up temporary files.
    Run this periodically to clean up old temp files.
    """
    import os
    import tempfile
    from datetime import datetime, timedelta
    
    logger.info("Starting temp file cleanup")
    
    temp_dir = tempfile.gettempdir()
    cutoff_time = datetime.now() - timedelta(hours=24)
    
    cleaned_count = 0
    
    for filename in os.listdir(temp_dir):
        file_path = os.path.join(temp_dir, filename)
        
        # Check if file is old enough
        file_mtime = datetime.fromtimestamp(os.path.getmtime(file_path))
        if file_mtime < cutoff_time:
            try:
                # Check if it's a temp file (starts with uuid pattern)
                if any(filename.startswith(prefix) for prefix in ["uuid", "tmp"]):
                    os.remove(file_path)
                    cleaned_count += 1
            except Exception as e:
                logger.warning(f"Failed to delete temp file {filename}: {str(e)}")
    
    logger.info(f"Temp file cleanup completed: {cleaned_count} files removed")
    return {"cleaned_count": cleaned_count}
