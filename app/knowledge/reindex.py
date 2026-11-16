"""Re-embed and index active FAQ records that were stored before vectors were configured."""
import asyncio
from sqlalchemy import text
from app.database.connection import SessionLocal
from app.knowledge.indexing import index_chunks

async def reindex_faqs(source_id: str | None=None):
    db=SessionLocal()
    try:
        records=db.execute(text("""SELECT f.id AS faq_id,f.source_id,f.document_id,f.question,f.answer,f.category,
          f.language,f.content_hash,s.source_name,s.source_url FROM knowledge_faqs f
          JOIN knowledge_sources s ON s.id=f.source_id
          WHERE f.status='ACTIVE' AND (CAST(:source_id AS uuid) IS NULL OR f.source_id=CAST(:source_id AS uuid))
          ORDER BY f.created_at"""),{"source_id":source_id}).mappings().all()
        batch=[]
        for r in records:
            payload={"source_id":str(r["source_id"]),"document_id":str(r["document_id"]) if r["document_id"] else None,
              "faq_id":str(r["faq_id"]),"question":r["question"],"answer":r["answer"],"category":r["category"],
              "source_name":r["source_name"],"source_url":r["source_url"],"content_type":"faq","language":r["language"],
              "content_hash":r["content_hash"],"chunk_index":0}
            batch.append({"text":f"Question: {r['question']}\nAnswer: {r['answer']}","payload":payload})
    finally: db.close()
    count=await index_chunks(batch)
    return {"faqs_indexed":count}

if __name__ == "__main__":
    import argparse
    parser=argparse.ArgumentParser(description="Index stored GoodBooks FAQs into Qdrant")
    parser.add_argument("--source-id")
    args=parser.parse_args()
    print(asyncio.run(reindex_faqs(args.source_id)))
