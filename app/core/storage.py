"""Supabase Storage operations for media assets"""
import asyncio
import mimetypes
import time
from supabase import Client
from config import settings
from pathlib import Path
from typing import Optional
import uuid

from app.utils.api_logger import ApiCallTimer


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

        # Supabase Storage rejects audio/x-wav; use the standard audio/wav
        if mime_type == "audio/x-wav":
            mime_type = "audio/wav"

        def _do_upload():
            with open(file_path, 'rb') as f:
                file_bytes = f.read()
            # Retry with exponential backoff for transient network issues
            for attempt in range(1, 4):
                try:
                    self.client.storage.from_(self.bucket_name).upload(
                        object_name,
                        file_bytes,
                        file_options={"content-type": mime_type}
                    )
                    return self.client.storage.from_(self.bucket_name).get_public_url(object_name)
                except Exception as exc:
                    if attempt == 3:
                        raise
                    time.sleep(2 ** attempt)  # 2s, 4s

        with ApiCallTimer("SupabaseStorage", "upload", f"bucket={self.bucket_name},object={object_name}") as timer:
            result = await asyncio.to_thread(_do_upload)
            timer.status = "200 OK"
        return result

    async def delete_file(self, object_name: str) -> bool:
        """
        Delete a file from Supabase Storage.

        Args:
            object_name: Name of the object to delete

        Returns:
            True if successful, False otherwise
        """
        def _do_delete():
            try:
                self.client.storage.from_(self.bucket_name).remove([object_name])
                return True
            except Exception:
                return False

        with ApiCallTimer("SupabaseStorage", "delete", f"bucket={self.bucket_name},object={object_name}") as timer:
            result = await asyncio.to_thread(_do_delete)
            timer.status = "200 OK" if result else "error"
        return result
    
    def get_public_url(self, object_name: str) -> str:
        """
        Get public URL for a storage object.
        
        Args:
            object_name: Name of the object
            
        Returns:
            Public URL
        """
        return self.client.storage.from_(self.bucket_name).get_public_url(object_name)
