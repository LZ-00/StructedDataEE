import pytest

from app.services.extraction.document_loader import DocumentLoadError, load_document


def test_load_txt_utf8():
    raw = "材料 A 在 800°C 下烧结 2 h。".encode("utf-8")
    text, warnings = load_document(raw, "report.txt")
    assert "800°C" in text
    assert warnings == []


def test_load_empty_raises():
    with pytest.raises(DocumentLoadError):
        load_document(b"", "empty.txt")


def test_unsupported_extension():
    with pytest.raises(DocumentLoadError):
        load_document(b"data", "file.docx")
