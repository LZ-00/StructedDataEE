"""PDF / TXT 文档解析为纯文本。"""

from __future__ import annotations

import io
from typing import Optional


class DocumentLoadError(ValueError):
    pass


def load_document(raw: bytes, filename: Optional[str] = None) -> tuple[str, list[str]]:
    """
    将上传字节解析为全文文本。
    返回 (text, warnings)。
    """
    name = (filename or "").lower().strip()
    warnings: list[str] = []

    if not raw:
        raise DocumentLoadError("上传文件为空")

    if name.endswith(".pdf"):
        text, pdf_warnings = _load_pdf(raw)
        warnings.extend(pdf_warnings)
    elif name.endswith(".txt") or not name:
        text = raw.decode("utf-8", errors="replace")
    else:
        raise DocumentLoadError("仅支持 PDF 与 TXT 格式")

    text = (text or "").strip()
    if not text:
        raise DocumentLoadError("未能从文档中解析出有效文本")
    return text, warnings


def _load_pdf(raw: bytes) -> tuple[str, list[str]]:
    warnings: list[str] = []
    try:
        from pypdf import PdfReader
    except ImportError as e:
        raise DocumentLoadError("PDF 解析依赖未安装，请安装 pypdf") from e

    reader = PdfReader(io.BytesIO(raw))
    parts: list[str] = []
    for page in reader.pages:
        page_text = page.extract_text() or ""
        if page_text.strip():
            parts.append(page_text.strip())

    if not parts:
        warnings.append("PDF 未提取到文本层内容，扫描件需 OCR（当前未支持）")
        return "", warnings

    return "\n\n".join(parts), warnings
