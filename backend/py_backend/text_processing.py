import re
from pathlib import Path


def extract_text_from_pdf(file_path: str | Path) -> str:
    try:
        from pypdf import PdfReader
        reader = PdfReader(str(file_path))
        return "\n".join(page.extract_text() or "" for page in reader.pages).strip()
    except Exception as exc:
        raise RuntimeError(f"PDF text extraction failed: {exc}") from exc


def extract_text_from_image(file_path: str | Path) -> str:
    try:
        import pytesseract
        from PIL import Image
        return pytesseract.image_to_string(Image.open(file_path)).strip()
    except Exception as exc:
        raise RuntimeError(f"Image OCR failed: {exc}") from exc


def infer_chapters_locally(text: str, title: str | None = None):
    fallback = [title or "Introduction", "Core Concepts", "Practice"]
    if not text:
        return fallback

    lines = [line.strip() for line in text.splitlines() if line.strip()]
    chapter_lines = [
        line for line in lines
        if re.search(r"^(chapter|unit|lesson|topic)\s+[\divx]+[:.)\-\s]", line, re.I)
        or re.search(r"^[\d]+[.)]\s+[A-Z][A-Za-z\s-]{3,80}$", line)
    ]
    cleaned = []
    for line in chapter_lines:
        value = re.sub(r"^(chapter|unit|lesson|topic)\s+", "", line, flags=re.I).strip()
        if value not in cleaned:
            cleaned.append(value)
    return cleaned[:20] if cleaned else fallback


def split_sentences(text: str):
    normalized = re.sub(r"\s+", " ", text or "").strip()
    return [sentence.strip() for sentence in re.split(r"(?<=[.!?])\s+", normalized) if len(sentence.strip()) > 20]
