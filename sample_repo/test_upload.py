"""Comprehensive unit and edge-case test suite for FileUploadService."""

import pytest
from upload import FileUploadService

@pytest.fixture
def service():
    return FileUploadService()

def test_valid_pdf_under_10mb(service):
    """PDF under 10MB should upload successfully."""
    content = b"%PDF-1.4 " + b"0" * (1024 * 1024)  # 1MB PDF
    result = service.process_upload("document.pdf", content)
    assert result["status"] == "success"
    assert result["filename"] == "document.pdf"

def test_invalid_extension(service):
    """Unsupported extensions should raise ValueError."""
    with pytest.raises(ValueError, match="Unsupported file format"):
        service.process_upload("script.exe", b"binary")

def test_empty_filename(service):
    """Empty filename should raise ValueError."""
    with pytest.raises(ValueError, match="Filename cannot be empty"):
        service.process_upload("", b"data")

def test_exact_10mb_boundary(service):
    """Exact 10 MB file (10 * 1024 * 1024 bytes) must be permitted and accepted."""
    content = b"%PDF-1.4 " + b"0" * (10 * 1024 * 1024 - 9)  # Exactly 10MB
    assert len(content) == 10 * 1024 * 1024
    result = service.process_upload("exact_10mb.pdf", content)
    assert result["status"] == "success"
    assert result["size"] == 10 * 1024 * 1024

def test_large_pdf_upload_over_10mb(service):
    """Files over 10MB must be rejected cleanly, NOT crash with unhandled 500 error."""
    content = b"%PDF-1.4 " + b"0" * (11 * 1024 * 1024)  # 11MB PDF
    result = service.process_upload("large_document.pdf", content)
    assert result["status"] == "rejected"
    assert "exceeds" in result.get("error", "").lower()
