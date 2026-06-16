"""Supabase database connection and repository layer"""
from supabase import create_client, Client
from config import settings
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone
from app.utils.logger import get_logger

logger = get_logger("vibetale")


class Database:
    """Singleton database connection manager with connection pooling"""
    
    _instance: Optional['Database'] = None
    _client: Optional[Client] = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if self._client is None:
            # Configure httpx limits for connection pooling
            import httpx
            limits = httpx.Limits(
                max_connections=settings.db_pool_maxsize,
                max_keepalive_connections=settings.db_pool_connections
            )
            
            # Configure timeouts
            timeout = httpx.Timeout(
                connect=settings.db_connection_timeout,
                read=settings.db_read_timeout,
                write=settings.db_write_timeout,
                pool=5.0
            )
            
            # Create client (simple initialization for compatibility)
            self._client = create_client(
                settings.supabase_url,
                settings.supabase_service_key
            )
            
            logger.info(f"Database connection pool configured: max_connections={settings.db_pool_maxsize}, keepalive={settings.db_pool_connections}")
    
    @property
    def client(self) -> Client:
        """Get Supabase client"""
        return self._client


# Repository classes for clean separation of concerns
class BookRepository:
    """Repository for book-related database operations"""
    
    def __init__(self, db: Database = None):
        self.db = db or Database()
    
    def create(self, book_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new book record"""
        response = self.db.client.table('books').insert(book_data).execute()
        return response.data[0] if response.data else None
    
    def get_by_id(self, book_id: str) -> Optional[Dict[str, Any]]:
        """Get a book by ID"""
        response = self.db.client.table('books').select('*').eq('id', book_id).execute()
        return response.data[0] if response.data else None
    
    def get_by_user(self, user_id: str) -> List[Dict[str, Any]]:
        """Get all books for a user"""
        response = self.db.client.table('books').select('*').eq('user_id', user_id).execute()
        return response.data
    
    def update(self, book_id: str, update_data: Dict[str, Any]) -> Dict[str, Any]:
        """Update a book record"""
        response = self.db.client.table('books').update(update_data).eq('id', book_id).execute()
        return response.data[0] if response.data else None
    
    def delete(self, book_id: str) -> bool:
        """Delete a book record"""
        response = self.db.client.table('books').delete().eq('id', book_id).execute()
        return len(response.data) > 0

    def get_public(self, category: Optional[str] = None, limit: int = 100) -> List[Dict[str, Any]]:
        """Public, processed books for the discovery catalog."""
        query = self.db.client.table('books').select('*').eq(
            'is_public', True).eq('processing_status', 'completed')
        if category:
            query = query.eq('genre', category)
        response = query.limit(limit).execute()
        return response.data or []

    def get_public_categories(self) -> List[str]:
        """Distinct genres across public books."""
        response = self.db.client.table('books').select('genre').eq(
            'is_public', True).eq('processing_status', 'completed').execute()
        seen = []
        for row in (response.data or []):
            g = row.get('genre')
            if g and g not in seen:
                seen.append(g)
        return seen


class ChapterRepository:
    """Repository for chapter-related database operations"""
    
    def __init__(self, db: Database = None):
        self.db = db or Database()
    
    def create(self, chapter_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new chapter record"""
        response = self.db.client.table('chapters').insert(chapter_data).execute()
        return response.data[0] if response.data else None
    
    def get_by_book(self, book_id: str) -> List[Dict[str, Any]]:
        """Get all chapters for a book"""
        response = self.db.client.table('chapters').select('*').eq('book_id', book_id).order('chapter_number').execute()
        return response.data
    
    def get_by_id(self, chapter_id: str) -> Optional[Dict[str, Any]]:
        """Get a chapter by ID"""
        response = self.db.client.table('chapters').select('*').eq('id', chapter_id).execute()
        return response.data[0] if response.data else None


class TextChunkRepository:
    """Repository for text chunk database operations"""
    
    def __init__(self, db: Database = None):
        self.db = db or Database()
    
    def create(self, chunk_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new text chunk record"""
        response = self.db.client.table('text_chunks').insert(chunk_data).execute()
        return response.data[0] if response.data else None
    
    def get_by_id(self, chunk_id: str) -> Optional[Dict[str, Any]]:
        """Get a text chunk by ID"""
        response = self.db.client.table('text_chunks').select('*').eq('id', chunk_id).execute()
        return response.data[0] if response.data else None
    
    def get_by_chapter(self, chapter_id: str) -> List[Dict[str, Any]]:
        """Get all text chunks for a chapter"""
        response = self.db.client.table('text_chunks').select('*').eq('chapter_id', chapter_id).order('order').execute()
        return response.data
    
    def get_by_book(self, book_id: str) -> List[Dict[str, Any]]:
        """Get all text chunks for a book with chapter_number joined"""
        response = self.db.client.table('text_chunks').select(
            '*, chapters(chapter_number)'
        ).eq('book_id', book_id).order('order').execute()
        # Flatten nested chapters dict into chapter_number field
        for chunk in (response.data or []):
            chapters = chunk.get('chapters')
            if isinstance(chapters, list) and chapters:
                chunk['chapter_number'] = chapters[0].get('chapter_number')
            elif isinstance(chapters, dict):
                chunk['chapter_number'] = chapters.get('chapter_number')
            if 'chapters' in chunk:
                del chunk['chapters']
        return response.data
    
    def update(self, chunk_id: str, update_data: Dict[str, Any]) -> Dict[str, Any]:
        """Update a text chunk record"""
        response = self.db.client.table('text_chunks').update(update_data).eq('id', chunk_id).execute()
        return response.data[0] if response.data else None


class ReadingProgressRepository:
    """Repository for reading progress database operations"""
    
    def __init__(self, db: Database = None):
        self.db = db or Database()
    
    def get_progress(self, user_id: str, book_id: str) -> Optional[Dict[str, Any]]:
        """Get reading progress for a user-book pair"""
        response = self.db.client.table('reading_progress').select('*').eq('user_id', user_id).eq('book_id', book_id).execute()
        return response.data[0] if response.data else None
    
    def upsert(self, progress_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create or update reading progress"""
        user_id = progress_data['user_id']
        book_id = progress_data['book_id']
        
        # Check if exists
        existing = self.get_progress(user_id, book_id)
        
        if existing:
            response = self.db.client.table('reading_progress').update(progress_data).eq('id', existing['id']).execute()
        else:
            response = self.db.client.table('reading_progress').insert(progress_data).execute()

        return response.data[0] if response.data else None


class UserLibraryRepository:
    """Repository for the per-user library (reading status + favorites)."""

    def __init__(self, db: Database = None):
        self.db = db or Database()

    def get_entry(self, user_id: str, book_id: str) -> Optional[Dict[str, Any]]:
        """Get a user's library entry for a book."""
        response = self.db.client.table('user_library').select('*').eq(
            'user_id', user_id).eq('book_id', book_id).execute()
        return response.data[0] if response.data else None

    def list_for_user(self, user_id: str) -> List[Dict[str, Any]]:
        """List a user's library entries with the joined book record."""
        response = self.db.client.table('user_library').select(
            '*, books(*)').eq('user_id', user_id).execute()
        return response.data or []

    def set_state(
        self,
        user_id: str,
        book_id: str,
        reading_status: Optional[str] = None,
        is_favorite: Optional[bool] = None,
    ) -> Dict[str, Any]:
        """Create or update a library entry; adds the book if not present."""
        existing = self.get_entry(user_id, book_id)
        data: Dict[str, Any] = {'updated_at': datetime.now(timezone.utc).isoformat()}
        if reading_status is not None:
            data['reading_status'] = reading_status
        if is_favorite is not None:
            data['is_favorite'] = is_favorite

        if existing:
            response = self.db.client.table('user_library').update(data).eq(
                'id', existing['id']).execute()
        else:
            data['user_id'] = user_id
            data['book_id'] = book_id
            response = self.db.client.table('user_library').insert(data).execute()
        return response.data[0] if response.data else None

    def add_if_absent(self, user_id: str, book_id: str, reading_status: str = 'reading') -> None:
        """Ensure a library entry exists (used on upload)."""
        if not self.get_entry(user_id, book_id):
            self.db.client.table('user_library').insert({
                'user_id': user_id,
                'book_id': book_id,
                'reading_status': reading_status,
            }).execute()

    def remove(self, user_id: str, book_id: str) -> bool:
        """Remove a book from the user's library."""
        response = self.db.client.table('user_library').delete().eq(
            'user_id', user_id).eq('book_id', book_id).execute()
        return len(response.data) > 0
