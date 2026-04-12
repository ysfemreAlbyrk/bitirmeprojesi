"""Book-related models"""
from pydantic import BaseModel, Field
from datetime import datetime
from enum import Enum
from typing import Optional


class BookFormat(str, Enum):
    EPUB = "epub"
    PDF = "pdf"


class ProcessingStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class AuditResult(str, Enum):
    APPROVED = "approved"
    COPYRIGHT_SUSPICIOUS = "copyright_suspicious"
    ETHICS_VIOLATION = "ethics_violation"
    AUDIT_FAILED = "audit_failed"


class Book(BaseModel):
    id: str
    user_id: str
    title: str
    author: str
    format: BookFormat
    file_size: int
    file_url: str
    upload_date: datetime
    processing_status: ProcessingStatus = ProcessingStatus.PENDING
    audit_result: Optional[AuditResult] = None
    total_pages: Optional[int] = None
    cover_url: Optional[str] = None
    
    class Config:
        use_enum_values = True


class BookCreate(BaseModel):
    user_id: str
    title: str
    author: str
    format: BookFormat
    file_size: int
    file_url: str
    total_pages: Optional[int] = None


class BookUpdate(BaseModel):
    processing_status: Optional[ProcessingStatus] = None
    audit_result: Optional[AuditResult] = None
    cover_url: Optional[str] = None


class BookResponse(BaseModel):
    id: str
    title: str
    author: str
    format: BookFormat
    processing_status: ProcessingStatus
    audit_result: Optional[AuditResult] = None
    cover_url: Optional[str] = None
    upload_date: datetime
    last_read_date: Optional[datetime] = None
    
    class Config:
        use_enum_values = True
