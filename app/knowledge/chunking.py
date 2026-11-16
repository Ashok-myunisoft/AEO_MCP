from app.config.settings import settings

def chunk_text(text: str, size: int | None = None, overlap: int | None = None):
    size=size or settings.CHUNK_SIZE; overlap=settings.CHUNK_OVERLAP if overlap is None else overlap
    if size < 1 or overlap < 0 or overlap >= size: raise ValueError("Invalid chunk size/overlap")
    text=text.strip(); chunks=[]; start=0
    while start < len(text):
        end=min(len(text),start+size)
        if end < len(text):
            boundary=max(text.rfind("\n",start,end),text.rfind(". ",start,end))
            if boundary > start+size//2: end=boundary+1
        chunks.append(text[start:end].strip()); start=max(end-overlap,start+1)
    return [c for c in chunks if c]

def faq_chunks(question, answer): return [f"Question: {question.strip()}\nAnswer: {answer.strip()}"]
