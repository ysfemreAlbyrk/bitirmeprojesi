"""Supabase Storage operations for media assets"""
import mimetypes
from supabase import Client
from config import settings
from pathlib import Path
from typing import Optional
import uuid


class StorageService:
    """Service for managing Supabase Object Storage operations"""
    
    def __init__(self, client: Client):
        self.client = client
        self.bucket_name = settings.storage_bucket_name
    
    async def upload_file(
        self,
        file_path: str,
        object_name: Optional[str] = None
    ) -> str:
        """
        Upload a file to Supabase Storage.
        
        Args:
            file_path: Local path to the file
            object_name: Name for the object in storage (auto-generated if None)
            
        Returns:
            Public URL of the uploaded file
        """
        if object_name is None:
            object_name = f"{uuid.uuid4()}_{Path(file_path).name}"
        
        mime_type, _ = mimetypes.guess_type(file_path)
        if mime_type is None:
            mime_type = "application/octet-stream"

        with open(file_path, 'rb') as f:
            self.client.storage.from_(self.bucket_name).upload(
                object_name,
                f.read(),
                file_options={"content-type": mime_type}
            )
        
        # Get public URL
        return self.client.storage.from_(self.bucket_name).get_public_url(object_name)
    
    async def delete_file(self, object_name: str) -> bool:
        """
        Delete a file from Supabase Storage.
        
        Args:
            object_name: Name of the object to delete
            
        Returns:
            True if successful, False otherwise
        """
        try:
            self.client.storage.from_(self.bucket_name).remove([object_name])
            return True
        except Exception:
            return False
    
    def get_public_url(self, object_name: str) -> str:
        """
        Get public URL for a storage object.
        
        Args:
            object_name: Name of the object
            
        Returns:
            Public URL
        """
        return self.client.storage.from_(self.bucket_name).get_public_url(object_name)
