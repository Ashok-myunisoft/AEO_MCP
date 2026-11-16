import hashlib
from app.knowledge.chunking import chunk_text, faq_chunks
from app.knowledge.indexing import index_chunks

def normalize(text): return " ".join(text.replace("\x00","").split())
def content_hash(text): return hashlib.sha256(normalize(text).encode("utf-8")).hexdigest()
async def process_knowledge(records):
    chunks=[]
    for r in records:
        parts=faq_chunks(r["question"],r["answer"]) if r.get("question") else chunk_text(normalize(r.get("text","")))
        for i,part in enumerate(parts): chunks.append({"text":part,"point_id":r.get("point_id"),"payload":{**r.get("payload",{}),"chunk_index":i,"content_hash":content_hash(part)}})
    return await index_chunks(chunks)
