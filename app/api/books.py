"""Book management API endpoints"""
from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from typing import List
import uuid
from pathlib import Path
import aiofiles
from app.utils.logger import get_logger
from app.utils.file_validator import FileValidator, FileValidationError
from app.utils.pagination import PaginatedResponse, PaginationParams, paginate
from app.middleware.rate_limit import limiter
from app.tasks.book_tasks import process_book_async

logger = get_logger("vibetale")

from app.models.book import Book, BookCreate, BookResponse, ProcessingStatus
from app.core.database import BookRepository
from app.services.book_processing_service import BookProcessingService
from app.core.storage import StorageService
from app.core.dependencies import (
    get_book_processing_service,
    get_book_repository,
    get_storage_service
)
from config import settings

router = APIRouter(prefix="/books", tags=["books"])


@router.post("/upload", response_model=BookResponse)
async def upload_book(
    file: UploadFile = File(...),
    user_id: str = None,
    processing_service: BookProcessingService = Depends(get_book_processing_service),
    storage_service: StorageService = Depends(get_storage_service),
    book_repo: BookRepository = Depends(get_book_repository)
):
    """Upload and process a new book"""
    logger.info(f"Book upload request received: {file.filename} from user {user_id}")
    
    # Read file content
    file_content = await file.read()
    file_size = len(file_content)
    
    # Save file temporarily for validation
    temp_file_path = Path(f"/tmp/{uuid.uuid4()}_{file.filename}")
    async with aiofiles.open(temp_file_path, 'wb') as f:
        await f.write(file_content)
    
    logger.debug(f"Temporary file created: {temp_file_path}")
    
    try:
        # Perform complete file validation
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
        
        # Extract metadata (simplified - in production, extract from file)
        book_create = BookCreate(
            user_id=user_id or str(uuid.uuid4()),  # Temporary user ID
            title=file.filename,  # Extract from file in production
            author="Unknown",  # Extract from file in production
            format=validation_result['extension'].lstrip('.'),
            file_size=file_size,
            file_url=None
        )
        
        # Upload to Supabase Storage
        logger.debug("Uploading file to storage")
        file_url = await storage_service.upload_file(str(temp_file_path))
        
        # Create book record
        book_data = book_create.model_dump()
        book_data['id'] = str(uuid.uuid4())
        book_data['file_url'] = file_url
        book_record = book_repo.create(book_data)
        
        # Start processing in background using Celery
        logger.info(f"Submitting book processing task to Celery: {book_record['id']}")
        process_book_async.delay(
            book_id=book_record['id'],
            file_path=str(temp_file_path),
            file_format=validation_result['extension'].lstrip('.')
        )
        
        logger.info(f"Book upload completed: {book_record['id']}")
        return BookResponse(**book_record)
        
    except Exception as e:
        logger.error(f"Book upload failed: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
        
    finally:
        # Clean up temp file
        if temp_file_path.exists():
            temp_file_path.unlink()
            logger.debug(f"Temporary file removed: {temp_file_path}")


@router.get("/", response_model=PaginatedResponse[BookResponse])
@limiter.limit("60/minute")  # 60 requests per minute per IP
async def list_books(
    user_id: str,
    pagination: PaginationParams = Depends(),
    book_repo: BookRepository = Depends(get_book_repository)
):
    """
    List all books for a user with pagination.
    """
    all_books = book_repo.get_by_user(user_id)
    total = len(all_books)
    
    # Apply pagination
    paginated_items = all_books[pagination.offset:pagination.offset + pagination.page_size]
    
    return paginate(
        items=[BookResponse(**book) for book in paginated_items],
        total=total,
        params=pagination
    )


@router.get("/{book_id}", response_model=BookResponse)
async def get_book(
    book_id: str,
    book_repo: BookRepository = Depends(get_book_repository)
):
    """
    Get book details by ID.
    """
    book = book_repo.get_by_id(book_id)
    
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
    
    return BookResponse(**book)


@router.get("/{book_id}/status")
async def get_book_status(
    book_id: str,
    book_repo: BookRepository = Depends(get_book_repository)
):
    """
    Get processing status of a book.
    """
    book = book_repo.get_by_id(book_id)
    
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
    
    return {
        "book_id": book_id,
        "processing_status": book['processing_status'],
        "audit_result": book.get('audit_result')
    }


@router.delete("/{book_id}")
async def delete_book(
    book_id: str,
    book_repo: BookRepository = Depends(get_book_repository)
):
    """
    Delete a book and all associated media.
    """
    book = book_repo.get_by_id(book_id)
    
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
    
    # Delete book record (cascade delete should handle related records in production)
    success = book_repo.delete(book_id)
    
    if success:
        return {"message": "Book deleted successfully"}
    else:
        raise HTTPException(status_code=500, detail="Failed to delete book")
