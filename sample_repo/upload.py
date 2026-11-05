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

        if file_size > self.MAX_FILE_SIZE:
            return {
                "valid": False,
                "filename": filename,
                "size": file_size,
                "content_type": "application/pdf" if ext == ".pdf" else "application/octet-stream",
                "error": f"File size {file_size} exceeds maximum permitted limit of 10 MB"
            }

        return {
            "valid": True,
            "filename": filename,
            "size": file_size,
            "content_type": "application/pdf" if ext == ".pdf" else "application/octet-stream"
        }

    def process_upload(self, filename: str, content: bytes) -> Dict[str, Any]:
        """Process file upload safely."""
        validation = self.validate_file(filename, content)
        if not validation.get("valid", False):
            return {
                "status": "rejected",
                "filename": validation["filename"],
                "size": validation["size"],
                "error": validation.get("error", "Validation failed")
            }

        return {
            "status": "success",
            "filename": filename,
            "size": validation["size"],
            "content_type": validation["content_type"]
        }
