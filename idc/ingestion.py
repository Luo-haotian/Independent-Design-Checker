"""Page-preserving PDF ingestion and context-safe chunking."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol

import pymupdf as fitz
from PIL import Image


class ImageOcr(Protocol):
    available: bool

    def extract_text_from_image(self, image: Image.Image) -> str: ...


@dataclass(slots=True)
class PageContent:
    page_number: int
    text: str
    extraction_method: str
    confidence: float
    embedded_images: int = 0
    low_text: bool = False

    @property
    def labelled_text(self) -> str:
        return f"--- Page {self.page_number} ({self.extraction_method}) ---\n{self.text.strip()}"


@dataclass(slots=True)
class DocumentExtraction:
    source_path: str
    source_sha256: str
    pages: list[PageContent] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def page_count(self) -> int:
        return len(self.pages)

    @property
    def processed_pages(self) -> list[int]:
        return [page.page_number for page in self.pages if page.text.strip()]

    @property
    def unprocessed_pages(self) -> list[int]:
        return [page.page_number for page in self.pages if not page.text.strip()]

    @property
    def full_text(self) -> str:
        return "\n\n".join(page.labelled_text for page in self.pages if page.text.strip())

    @property
    def embedded_images(self) -> int:
        return sum(page.embedded_images for page in self.pages)

    @property
    def used_ocr(self) -> bool:
        return any(page.extraction_method == "ocr" for page in self.pages)


@dataclass(slots=True)
class DocumentChunk:
    index: int
    page_numbers: list[int]
    content: str


def sha256_file(path: str | Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def ingest_pdf(
    pdf_path: str | Path,
    *,
    ocr: ImageOcr | None = None,
    force_ocr: bool = False,
    low_text_threshold: int = 50,
) -> DocumentExtraction:
    """Extract every PDF page and retain page-level provenance."""
    path = Path(pdf_path)
    extraction = DocumentExtraction(source_path=str(path), source_sha256=sha256_file(path))
    document = fitz.open(path)
    try:
        for page_number, page in enumerate(document, start=1):
            text = page.get_text() or ""
            low_text = len(text.strip()) < low_text_threshold
            method = "text"
            confidence = 1.0 if not low_text else 0.55

            if (force_ocr or low_text) and ocr and ocr.available:
                pixmap = page.get_pixmap(matrix=fitz.Matrix(2, 2), alpha=False)
                image = Image.frombytes("RGB", [pixmap.width, pixmap.height], pixmap.samples)
                ocr_text = ocr.extract_text_from_image(image)
                if ocr_text.strip():
                    text = ocr_text
                    method = "ocr"
                    confidence = 0.75

            if not text.strip():
                extraction.warnings.append(f"Page {page_number} has no readable text.")
                confidence = 0.0

            extraction.pages.append(
                PageContent(
                    page_number=page_number,
                    text=text,
                    extraction_method=method,
                    confidence=confidence,
                    embedded_images=len(page.get_images()),
                    low_text=low_text,
                )
            )
    finally:
        document.close()
    return extraction


def build_page_chunks(extraction: DocumentExtraction, max_chars: int) -> list[DocumentChunk]:
    """Build chunks without dropping pages; split oversized pages explicitly."""
    if max_chars <= 1000:
        raise ValueError("max_chars must be greater than 1000")

    chunks: list[DocumentChunk] = []
    current_parts: list[str] = []
    current_pages: list[int] = []
    current_size = 0

    def flush() -> None:
        nonlocal current_parts, current_pages, current_size
        if current_parts:
            chunks.append(DocumentChunk(len(chunks) + 1, list(dict.fromkeys(current_pages)), "\n\n".join(current_parts)))
        current_parts = []
        current_pages = []
        current_size = 0

    for page in extraction.pages:
        if not page.text.strip():
            continue
        labelled = page.labelled_text
        if len(labelled) > max_chars:
            flush()
            for offset in range(0, len(labelled), max_chars):
                segment = labelled[offset : offset + max_chars]
                chunks.append(DocumentChunk(len(chunks) + 1, [page.page_number], segment))
            continue
        if current_parts and current_size + len(labelled) + 2 > max_chars:
            flush()
        current_parts.append(labelled)
        current_pages.append(page.page_number)
        current_size += len(labelled) + 2
    flush()
    return chunks


def coverage_from_chunks(extraction: DocumentExtraction, chunks: list[DocumentChunk]) -> tuple[list[int], list[int]]:
    covered = sorted({page for chunk in chunks for page in chunk.page_numbers})
    missing = sorted(set(range(1, extraction.page_count + 1)) - set(covered))
    return covered, missing
