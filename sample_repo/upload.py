"""File upload service module."""

from typing import Dict, Any
import os

class FileUploadService:
    # 10 MB limit in bytes: 10 * 1024 * 1024 = 10,485,760 bytes
    MAX_FILE_SIZE = 10 * 1024 * 1024

    def __init__(self, storage_dir: str = "/tmp/uploads"):
        self.storage_dir = storage_dir

    def validate_file(self, filename: str, content: bytes) -> Dict[str, Any]:
        """Validate file name, extension, and content size."""
        if not filename:
            raise ValueError("Filename cannot be empty")

        ext = os.path.splitext(filename)[1].lower()
        if ext not in [".pdf", ".png", ".jpg", ".txt"]:
            raise ValueError(f"Unsupported file format: {ext}")

        file_size = len(content)

        # BUG: Incorrect size validation causing internal server error on files > 10MB
        # Instead of rejecting gracefully or handling chunked PDF processing,
        # it triggers an unexpected RuntimeError (simulating 500 error).
        if file_size > self.MAX_FILE_SIZE:
            raise RuntimeError(f"Buffer overflow: file size {file_size} exceeds internal buffer limit (500 Internal Server Error)")

        return {
            "valid": True,
            "filename": filename,
            "size": file_size,
            "content_type": "application/pdf" if ext == ".pdf" else "application/octet-stream"
        }

    def process_upload(self, filename: str, content: bytes) -> Dict[str, Any]:
        """Process file upload safely."""
        validation = self.validate_file(filename, content)
        return {
            "status": "success",
            "filename": validation["filename"],
            "size": validation["size"],
            "message": "File uploaded successfully"
        }
