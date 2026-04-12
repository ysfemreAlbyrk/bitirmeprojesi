"""Book management API endpoints"""
from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from typing import List
import uuid
from pathlib import Path
import aiofiles

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
    """
    Upload a book file (EPUB or PDF) and start processing.
    """
    # Validate file size
    file_content = await file.read()
    if len(file_content) > settings.max_file_size:
        raise HTTPException(status_code=400, detail="File size exceeds maximum allowed size")
    
    # Validate file format
    file_extension = Path(file.filename).suffix.lower().lstrip('.')
    if file_extension not in ['epub', 'pdf']:
        raise HTTPException(status_code=400, detail="Only EPUB and PDF files are supported")
    
    # Save file temporarily
    temp_file_path = Path(f"/tmp/{uuid.uuid4()}_{file.filename}")
    async with aiofiles.open(temp_file_path, 'wb') as f:
        await f.write(file_content)
    
    try:
        # Upload to Supabase Storage
        file_url = await storage_service.upload_file(str(temp_file_path))
        
        # Extract metadata (simplified - in production, extract from file)
        book_create = BookCreate(
            user_id=user_id or str(uuid.uuid4()),  # Temporary user ID
            title=file.filename,  # Extract from file in production
            author="Unknown",  # Extract from file in production
            format=file_extension,
            file_size=len(file_content),
            file_url=file_url
        )
        
        # Create book record
        book_data = book_create.model_dump()
        book_data['id'] = str(uuid.uuid4())
        book_record = book_repo.create(book_data)
        
        # Start processing in background
        import asyncio
        asyncio.create_task(
            processing_service.process_book(
                book_record['id'],
                str(temp_file_path),
                file_extension
            )
        )
        
        return BookResponse(**book_record)
        
    finally:
        # Clean up temp file
        if temp_file_path.exists():
            temp_file_path.unlink()


@router.get("/", response_model=List[BookResponse])
async def list_books(
    user_id: str,
    book_repo: BookRepository = Depends(get_book_repository)
):
    """
    List all books for a user.
    """
    books = book_repo.get_by_user(user_id)
    return [BookResponse(**book) for book in books]


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
