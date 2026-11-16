import uuid, json
from qdrant_client import QdrantClient, models
from app.config.settings import settings
from app.database.connection import SessionLocal
from sqlalchemy import text
from app.knowledge.embeddings import embed_texts

def client():
    # Qdrant is configured as a service endpoint; avoid sending that traffic through
    # workstation HTTP proxies, which commonly cannot route directly to Qdrant hosts.
    return QdrantClient(url=settings.QDRANT_URL,api_key=settings.QDRANT_API_KEY,timeout=15,trust_env=False)

async def index_chunks(records):
    if not records: return 0
    vectors=await embed_texts([x["text"] for x in records]); q=client()
    dim=len(vectors[0]); name=settings.QDRANT_COLLECTION
    if not q.collection_exists(name): q.create_collection(collection_name=name,vectors_config=models.VectorParams(size=dim,distance=models.Distance.COSINE))
    else:
        info=q.get_collection(name); actual=info.config.params.vectors.size
        if actual != dim: raise ValueError(f"Qdrant collection dimension {actual} does not match embedding dimension {dim}")
    points=[]; rows=[]
    for rec,vec in zip(records,vectors):
        payload=rec.get("payload",{})
        source_id=payload.get("source_id"); document_id=payload.get("document_id"); faq_id=payload.get("faq_id")
        if not source_id: raise ValueError("Each indexed chunk must include source_id")
        chunk_index=int(payload.get("chunk_index",0))
        stable_key=f"{source_id}:{document_id or ''}:{faq_id or ''}:{chunk_index}"
        pid=str(uuid.uuid5(uuid.NAMESPACE_URL,stable_key))
        payload={**payload,"chunk_index":chunk_index}
        points.append(models.PointStruct(id=pid,vector=vec,payload=payload))
        rows.append({"id":uuid.uuid5(uuid.NAMESPACE_URL,"db-chunk:"+stable_key),"faq_id":faq_id,"source_id":source_id,"document_id":document_id,"chunk_index":chunk_index,"chunk_text":rec["text"],"vector_point_id":pid,"embedding_model":settings.EMBEDDING_MODEL,"metadata":json.dumps(payload)})
    q.upsert(collection_name=name,points=points,wait=True)
    # PostgreSQL remains authoritative; upsert chunk references after Qdrant accepts vectors.
    db=SessionLocal()
    try:
        for row in rows:
            db.execute(text("""INSERT INTO knowledge_chunks
              (id,faq_id,source_id,document_id,chunk_index,chunk_text,vector_point_id,embedding_model,status,metadata,created_at)
              VALUES(:id,:faq_id,:source_id,:document_id,:chunk_index,:chunk_text,:vector_point_id,:embedding_model,'INDEXED',CAST(:metadata AS jsonb),now())
              ON CONFLICT (vector_point_id) DO UPDATE SET faq_id=EXCLUDED.faq_id,source_id=EXCLUDED.source_id,
              document_id=EXCLUDED.document_id,chunk_index=EXCLUDED.chunk_index,chunk_text=EXCLUDED.chunk_text,
              embedding_model=EXCLUDED.embedding_model,status='INDEXED',metadata=EXCLUDED.metadata"""),row)
        db.commit()
    except Exception:
        db.rollback(); raise
    finally: db.close()
    return len(points)
