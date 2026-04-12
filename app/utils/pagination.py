"""Pagination utilities for API responses"""
from typing import Generic, TypeVar, List, Optional
from pydantic import BaseModel, Field
from fastapi import Query

T = TypeVar('T')


class PaginatedResponse(BaseModel, Generic[T]):
    """Generic paginated response model"""
    items: List[T] = Field(..., description="List of items")
    total: int = Field(..., description="Total number of items")
    page: int = Field(..., description="Current page number (1-indexed)")
    page_size: int = Field(..., description="Number of items per page")
    total_pages: int = Field(..., description="Total number of pages")
    has_next: bool = Field(..., description="Whether there is a next page")
    has_previous: bool = Field(..., description="Whether there is a previous page")


class PaginationParams:
    """Pagination parameters for API endpoints"""
    
    def __init__(
        self,
        page: int = Query(1, ge=1, description="Page number (1-indexed)"),
        page_size: int = Query(10, ge=1, le=100, description="Number of items per page (max 100)")
    ):
        self.page = page
        self.page_size = page_size
        self.offset = (page - 1) * page_size


def paginate(items: List[T], total: int, params: PaginationParams) -> PaginatedResponse[T]:
    """
    Create a paginated response from a list of items.
    
    Args:
        items: List of items for the current page
        total: Total number of items across all pages
        params: Pagination parameters
        
    Returns:
        PaginatedResponse with metadata
    """
    total_pages = (total + params.page_size - 1) // params.page_size
    has_next = params.page < total_pages
    has_previous = params.page > 1
    
    return PaginatedResponse(
        items=items,
        total=total,
        page=params.page,
        page_size=params.page_size,
        total_pages=total_pages,
        has_next=has_next,
        has_previous=has_previous
    )
