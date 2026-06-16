"""Book management API endpoints"""
from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, Request
from typing import List
import uuid
from pathlib import Path
import aiofiles
from app.utils.logger import get_logger
from app.utils.file_validator import FileValidator, FileValidationError
from app.utils.pagination import PaginatedResponse, PaginationParams, paginate
from app.middleware.rate_limit import limiter
from app.tasks.book_tasks import process_book_async
from app.core.auth import get_current_user_id

logger = get_logger("vibetale")

from app.models.book import Book, BookCreate, BookResponse, ProcessingStatus
from app.core.database import BookRepository, TextChunkRepository, ChapterRepository
from app.services.book_processing_service import BookProcessingService
from app.core.storage import StorageService
from app.core.dependencies import (
    get_book_processing_service,
    get_book_repository,
    get_storage_service,
    get_text_chunk_repository,
    get_chapter_repository
)
from config import settings

router = APIRouter(prefix="/books", tags=["books"])


@router.post("/upload", response_model=BookResponse)
async def upload_book(
    file: UploadFile = File(...),
    processing_service: BookProcessingService = Depends(get_book_processing_service),
    storage_service: StorageService = Depends(get_storage_service),
    book_repo: BookRepository = Depends(get_book_repository),
    user_id: str = Depends(get_current_user_id),
):
    """Upload and process a new book"""
    logger.info(f"Book upload request received: {file.filename} from user {user_id}")

    file_content = await file.read()
    file_size = len(file_content)

    temp_file_path = Path(f"/tmp/{uuid.uuid4()}_{file.filename}")
    async with aiofiles.open(temp_file_path, 'wb') as f:
        await f.write(file_content)

    logger.debug(f"Temporary file created: {temp_file_path}")

    try:
        validation_result = FileValidator.validate_upload(
            filename=file.filename,
            file_size=file_size,
            file_path=str(temp_file_path)
        )

        if not validation_result['valid']:
            error_msg = f"File validation failed: {'; '.join(validation_result['errors'])}"
            logger.warning(error_msg)
            raise HTTPException(status_code=400, detail=error_msg)

        logger.info(f"File validation passed: {validation_result['mime_type']}")

        book_create = BookCreate(
            user_id=user_id,
            title=file.filename,
            author="Unknown",
            format=validation_result['extension'].lstrip('.'),
            file_size=file_size,
            file_url=None
        )

        logger.debug("Uploading file to storage")
        file_url = await storage_service.upload_file(str(temp_file_path))

        book_data = book_create.model_dump()
        book_data['id'] = str(uuid.uuid4())
        book_data['file_url'] = file_url
        book_record = book_repo.create(book_data)

        logger.info(f"Submitting book processing task to Celery: {book_record['id']}")
        process_book_async.delay(
            book_id=book_record['id'],
            file_path=str(temp_file_path),
            file_format=validation_result['extension'].lstrip('.')
        )

        logger.info(f"Book upload completed: {book_record['id']}")
        return BookResponse(**book_record)

    except HTTPException:
        # Clean up temp file on upload error only
        if temp_file_path.exists():
            temp_file_path.unlink()
            logger.debug(f"Temporary file removed after upload error: {temp_file_path}")
        raise
    except Exception as e:
        logger.error(f"Book upload failed: {str(e)}", exc_info=True)
        # Clean up temp file on upload error only
        if temp_file_path.exists():
            temp_file_path.unlink()
            logger.debug(f"Temporary file removed after upload error: {temp_file_path}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/", response_model=PaginatedResponse[BookResponse])
@limiter.limit("60/minute")
async def list_books(
    request: Request,
    pagination: PaginationParams = Depends(),
    book_repo: BookRepository = Depends(get_book_repository),
    user_id: str = Depends(get_current_user_id),
):
    """List all books for the authenticated user with pagination."""
    all_books = book_repo.get_by_user(user_id)
    total = len(all_books)

    paginated_items = all_books[pagination.offset:pagination.offset + pagination.page_size]

    return paginate(
        items=[BookResponse(**book) for book in paginated_items],
        total=total,
        params=pagination
    )


@router.get("/{book_id}", response_model=BookResponse)
async def get_book(
    book_id: str,
    book_repo: BookRepository = Depends(get_book_repository),
    user_id: str = Depends(get_current_user_id),
):
    """Get book details by ID."""
    book = book_repo.get_by_id(book_id)

    if not book:
        raise HTTPException(status_code=404, detail="Book not found")

    if book.get('user_id') != user_id:
        raise HTTPException(status_code=403, detail="Bu kitaba erişim izniniz yok")

    return BookResponse(**book)


@router.get("/{book_id}/status")
async def get_book_status(
    book_id: str,
    book_repo: BookRepository = Depends(get_book_repository),
    chunk_repo: TextChunkRepository = Depends(get_text_chunk_repository),
    chapter_repo: ChapterRepository = Depends(get_chapter_repository),
    user_id: str = Depends(get_current_user_id),
):
    """Get detailed processing status of a book with step-by-step progress."""
    book = book_repo.get_by_id(book_id)

    if not book:
        raise HTTPException(status_code=404, detail="Book not found")

    if book.get('user_id') != user_id:
        raise HTTPException(status_code=403, detail="Bu kitaba erişim izniniz yok")

    status = book['processing_status']
    audit = book.get('audit_result')

    # Gather chunk stats for step inference
    chunks = chunk_repo.get_by_book(book_id) or []
    total_chunks = len(chunks)
    analyzed = sum(1 for c in chunks if c.get('analyzed'))
    audio_count = sum(1 for c in chunks if c.get('audio_url'))
    image_count = sum(1 for c in chunks if c.get('image_url'))

    chapters = chapter_repo.get_by_book(book_id) or []

    # Build processing steps with completion inference
    audit_passed = audit is not None and audit != 'AUDIT_FAILED'
    steps = [
        {"name": "text_extraction", "label": "Metin Çıkarma", "completed": total_chunks > 0},
        {"name": "content_audit", "label": "İçerik Denetimi", "completed": audit_passed},
        {"name": "chapter_splitting", "label": "Bölüm Ayrıştırma", "completed": len(chapters) > 0},
        {"name": "semantic_chunking", "label": "Anlamsal Parçalama", "completed": total_chunks > 0},
        {"name": "scene_analysis", "label": "Sahne Analizi", "completed": total_chunks > 0 and analyzed >= total_chunks},
        {"name": "audio_generation", "label": "Ses Üretimi", "completed": total_chunks > 0 and audio_count >= total_chunks},
        {"name": "image_generation", "label": "Görsel Üretimi", "completed": total_chunks > 0 and image_count >= total_chunks},
    ]

    # Mark current step
    if status in ("processing", "pending"):
        for step in steps:
            if not step["completed"]:
                step["current"] = True
                break
    elif status == "failed":
        # Mark the first incomplete step as current to show where it failed
        for step in steps:
            if not step["completed"]:
                step["current"] = True
                break

    completed_steps = sum(1 for s in steps if s["completed"])
    progress = int((completed_steps / len(steps)) * 100) if steps else 0

    return {
        "book_id": book_id,
        "processing_status": status,
        "audit_result": audit,
        "progress_percent": progress,
        "total_chunks": total_chunks,
        "analyzed_chunks": analyzed,
        "audio_chunks": audio_count,
        "image_chunks": image_count,
        "steps": steps
    }


@router.get("/{book_id}/chunks")
async def get_book_chunks(
    book_id: str,
    chunk_repo: TextChunkRepository = Depends(get_text_chunk_repository),
    book_repo: BookRepository = Depends(get_book_repository),
    user_id: str = Depends(get_current_user_id),
):
    """Get all text chunks for a book, ordered by sequence (for the reader)."""
    book = book_repo.get_by_id(book_id)

    if not book:
        raise HTTPException(status_code=404, detail="Book not found")

    if book.get('user_id') != user_id:
        raise HTTPException(status_code=403, detail="Bu kitaba erişim izniniz yok")

    chunks = chunk_repo.get_by_book(book_id)

    return [
        {
            "chunk_id": chunk["id"],
            "sequence": chunk.get("order", idx),
            "content": chunk.get("text", ""),
            "chapter_id": chunk.get("chapter_id"),
            "chapter_number": chunk.get("chapter_number"),
            "has_audio": bool(chunk.get("audio_url")),
            "has_image": bool(chunk.get("image_url")),
        }
        for idx, chunk in enumerate(chunks)
    ]


@router.delete("/{book_id}")
async def delete_book(
    book_id: str,
    book_repo: BookRepository = Depends(get_book_repository),
    chunk_repo: TextChunkRepository = Depends(get_text_chunk_repository),
    storage_service: StorageService = Depends(get_storage_service),
    user_id: str = Depends(get_current_user_id),
):
    """Delete a book and all associated media."""
    book = book_repo.get_by_id(book_id)

    if not book:
        raise HTTPException(status_code=404, detail="Book not found")

    if book.get('user_id') != user_id:
        raise HTTPException(status_code=403, detail="Bu kitaba erişim izniniz yok")

    chunks = chunk_repo.get_by_book(book_id)
    deleted_media = 0
    for chunk in chunks:
        for field in ('audio_url', 'image_url'):
            url = chunk.get(field)
            if url:
                try:
                    object_name = url.split('/')[-1]
                    await storage_service.delete_file(object_name)
                    deleted_media += 1
                except Exception as e:
                    logger.warning(f"Failed to delete {field} for chunk {chunk['id']}: {e}")
    logger.info(f"Deleted {deleted_media} media assets for book {book_id}")

    success = book_repo.delete(book_id)

    if success:
        return {"message": "Book deleted successfully"}
    else:
        raise HTTPException(status_code=500, detail="Failed to delete book")
