import re

from .database import delete_where, filter_records, create_record


STOP_WORDS = {
    "the", "and", "for", "with", "that", "this", "from", "are", "was", "were", "have", "has",
    "not", "but", "you", "your", "his", "her", "their", "our", "can", "will", "shall", "what",
    "when", "where", "why", "how", "into", "about", "than", "then", "also", "they", "them",
}


def get_keywords(text: str):
    words = re.sub(r"[^a-z0-9\s]", " ", (text or "").lower()).split()
    unique = []
    for word in words:
        if len(word) > 2 and word not in STOP_WORDS and word not in unique:
            unique.append(word)
    return unique[:80]


def split_text_into_chunks(text: str, max_chars: int = 1400, overlap_chars: int = 180):
    normalized = re.sub(r"\s+", " ", text or "").strip()
    if not normalized:
        return []
    chunks = []
    start = 0
    while start < len(normalized):
        end = min(start + max_chars, len(normalized))
        chunks.append(normalized[start:end].strip())
        if end == len(normalized):
            break
        start = max(0, end - overlap_chars)
    return [chunk for chunk in chunks if chunk]


def infer_chunk_chapter(content: str, chapters: list[str]):
    lower = content.lower()
    return next((chapter for chapter in chapters if chapter.lower() in lower), chapters[0] if chapters else "")


def create_textbook_chunks(textbook_id: str, class_level: str, subject: str, chapters: list[str], text: str):
    delete_where("chunks", {"textbook_id": textbook_id})
    chunks = split_text_into_chunks(text)
    records = []
    for index, content in enumerate(chunks):
        records.append(create_record("chunks", {
            "textbook_id": textbook_id,
            "class_level": class_level,
            "subject": subject,
            "chapter": infer_chunk_chapter(content, chapters),
            "chunk_index": index,
            "content": content,
            "token_keywords": get_keywords(content),
            "metadata": {"source": "textbook_upload"},
        }))
    return records


def retrieve_relevant_chunks(textbook_id=None, class_level=None, subject=None, chapter=None, query=None, limit=5):
    chunks = filter_records("chunks", {
        "textbook_id": textbook_id,
        "class_level": class_level,
        "subject": subject,
    })
    query_keywords = get_keywords(f"{chapter or ''} {query or ''}")
    scored = []
    for chunk in chunks[:200]:
        content = (chunk.get("content") or "").lower()
        token_keywords = chunk.get("token_keywords") or []
        keyword_score = sum(3 if keyword in token_keywords else 1 if keyword in content else 0 for keyword in query_keywords)
        chapter_score = 5 if chapter and chapter.lower() in (chunk.get("chapter") or "").lower() else 0
        scored.append({**chunk, "score": keyword_score + chapter_score})
    scored.sort(key=lambda item: (-item["score"], item.get("chunk_index", 0)))
    return scored[:limit]
