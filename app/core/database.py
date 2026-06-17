"""Supabase database connection and repository layer"""
from supabase import create_client, Client
from config import settings
from typing import Optional, List, Dict, Any
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


class MediaAssetRepository:
    """Repository for media asset tracking"""

    def __init__(self, db: Database = None):
        self.db = db or Database()

    def create(self, asset_data: Dict[str, Any]) -> Dict[str, Any]:
        """Record a generated media asset (audio or image)"""
        response = self.db.client.table('media_assets').insert(asset_data).execute()
        return response.data[0] if response.data else None

    def get_by_chunk(self, chunk_id: str) -> List[Dict[str, Any]]:
        """Get all media assets for a text chunk"""
        response = self.db.client.table('media_assets').select('*').eq('chunk_id', chunk_id).execute()
        return response.data or []


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
