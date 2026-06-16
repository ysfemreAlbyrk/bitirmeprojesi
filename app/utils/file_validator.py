"""File validation utilities for secure file uploads"""
import magic
from typing import Tuple, Optional
from pathlib import Path
from config import settings
from app.utils.logger import get_logger

logger = get_logger("vibetale")


# Allowed MIME types for book uploads
ALLOWED_MIME_TYPES = {
    'application/epub+zip',
    'application/epub',
    'application/pdf',
    'application/x-pdf',
    'text/plain',
    'text/x-log',
    'application/msword',
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
}

# File extensions to MIME type mapping
EXTENSION_MIME_MAP = {
    '.epub': 'application/epub+zip',
    '.pdf': 'application/pdf',
    '.txt': 'text/plain',
    '.log': 'text/x-log',
    '.doc': 'application/msword',
    '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
}

# Magic bytes for file type verification
MAGIC_BYTES = {
    b'\x50\x4b\x03\x04': 'application/epub+zip',  # EPUB (ZIP)
    b'\x25\x50\x44\x46': 'application/pdf',       # PDF
    b'\xef\xbb\xbf': 'text/plain',              # UTF-8 BOM (TXT)
    b'\x50\x4b\x03\x04': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',  # DOCX (ZIP)
}


class FileValidationError(Exception):
    """Custom exception for file validation errors"""
    pass


class FileValidator:
    """Validator for secure file uploads"""
    
    @staticmethod
    def validate_file_size(file_size: int) -> None:
        """
        Validate file size against maximum allowed size.
        
        Args:
            file_size: Size of the file in bytes
            
        Raises:
            FileValidationError: If file size exceeds limit
        """
        if file_size > settings.max_file_size:
            error_msg = f"File size {file_size} bytes exceeds maximum allowed size of {settings.max_file_size} bytes"
            logger.warning(error_msg)
            raise FileValidationError(error_msg)
        
        logger.debug(f"File size validation passed: {file_size} bytes")
    
    @staticmethod
    def validate_file_extension(filename: str) -> Tuple[str, str]:
        """
        Validate file extension and return extension and expected MIME type.
        
        Args:
            filename: Name of the file
            
        Returns:
            Tuple of (extension, expected_mime_type)
            
        Raises:
            FileValidationError: If file extension is not allowed
        """
        ext = Path(filename).suffix.lower()
        
        if ext not in EXTENSION_MIME_MAP:
            error_msg = f"File extension '{ext}' is not allowed"
            logger.warning(error_msg)
            raise FileValidationError(error_msg)
        
        expected_mime = EXTENSION_MIME_MAP[ext]
        logger.debug(f"File extension validation passed: {ext} -> {expected_mime}")
        
        return ext, expected_mime
    
    @staticmethod
    def validate_mime_type(file_path: str, expected_mime: str) -> str:
        """
        Validate MIME type using python-magic library.
        
        Args:
            file_path: Path to the file
            expected_mime: Expected MIME type based on extension
            
        Returns:
            Actual MIME type detected
            
        Raises:
            FileValidationError: If MIME type doesn't match expected type
        """
        try:
            detected_mime = magic.from_file(file_path, mime=True)
            
            if detected_mime not in ALLOWED_MIME_TYPES:
                error_msg = f"Detected MIME type '{detected_mime}' is not allowed"
                logger.warning(error_msg)
                raise FileValidationError(error_msg)
            
            # Check if detected MIME matches expected MIME
            if detected_mime != expected_mime:
                # EPUB files might be detected as application/zip, which is acceptable
                if not (expected_mime == 'application/epub+zip' and detected_mime == 'application/zip'):
                    error_msg = f"MIME type mismatch: expected '{expected_mime}', detected '{detected_mime}'"
                    logger.warning(error_msg)
                    raise FileValidationError(error_msg)
            
            logger.debug(f"MIME type validation passed: {detected_mime}")
            return detected_mime
            
        except Exception as e:
            if isinstance(e, FileValidationError):
                raise
            error_msg = f"Failed to detect MIME type: {str(e)}"
            logger.error(error_msg)
            raise FileValidationError(error_msg)
    
    @staticmethod
    def validate_magic_bytes(file_path: str, expected_mime: str) -> None:
        """
        Validate file by checking magic bytes (file signature).
        
        Args:
            file_path: Path to the file
            expected_mime: Expected MIME type
            
        Raises:
            FileValidationError: If magic bytes don't match expected file type
        """
        try:
            with open(file_path, 'rb') as f:
                header = f.read(4)
            
            matched = False
            for magic_byte, mime_type in MAGIC_BYTES.items():
                if header.startswith(magic_byte):
                    # Check if it matches expected MIME type
                    if (mime_type == expected_mime or 
                        (expected_mime == 'application/epub+zip' and mime_type == 'application/epub+zip')):
                        matched = True
                        break
            
            if not matched:
                error_msg = f"File signature (magic bytes) does not match expected type '{expected_mime}'"
                logger.warning(error_msg)
                raise FileValidationError(error_msg)
            
            logger.debug("Magic bytes validation passed")
            
        except Exception as e:
            if isinstance(e, FileValidationError):
                raise
            error_msg = f"Failed to validate magic bytes: {str(e)}"
            logger.error(error_msg)
            raise FileValidationError(error_msg)
    
    @staticmethod
    def scan_for_malware(file_path: str) -> None:
        """
        Placeholder for malware scanning.
        
        In production, integrate with a virus scanning service like:
        - ClamAV (local)
        - VirusTotal API
        - AWS Macie
        - Google Cloud Virus Scanning
        
        Args:
            file_path: Path to the file
            
        Note:
            This is a placeholder. Implement actual scanning in production.
        """
        logger.debug(f"Malware scan placeholder for: {file_path}")
        # TODO: Integrate with actual malware scanning service
        # For now, we'll log a warning that scanning is not implemented
        logger.warning("Malware scanning not implemented - file uploaded without virus scan")
    
    @staticmethod
    def validate_upload(filename: str, file_size: int, file_path: str) -> dict:
        """
        Perform complete validation on uploaded file.
        
        Args:
            filename: Name of the uploaded file
            file_size: Size of the file in bytes
            file_path: Path to the temporary file
            
        Returns:
            Dictionary with validation results:
            {
                'valid': bool,
                'extension': str,
                'mime_type': str,
                'errors': list
            }
            
        Raises:
            FileValidationError: If any validation fails
        """
        errors = []
        
        try:
            # Step 1: Validate file size
            FileValidator.validate_file_size(file_size)
            
            # Step 2: Validate file extension
            extension, expected_mime = FileValidator.validate_file_extension(filename)
            
            # Step 3: Validate MIME type
            detected_mime = FileValidator.validate_mime_type(file_path, expected_mime)
            
            # Step 4: Validate magic bytes
            FileValidator.validate_magic_bytes(file_path, expected_mime)
            
            # Step 5: Malware scan (placeholder)
            FileValidator.scan_for_malware(file_path)
            
            logger.info(f"File validation successful: {filename} ({extension}, {detected_mime})")
            
            return {
                'valid': True,
                'extension': extension,
                'mime_type': detected_mime,
                'errors': []
            }
            
        except FileValidationError as e:
            errors.append(str(e))
            logger.error(f"File validation failed: {filename} - {str(e)}")
            return {
                'valid': False,
                'extension': extension if 'extension' in locals() else None,
                'mime_type': None,
                'errors': errors
            }
