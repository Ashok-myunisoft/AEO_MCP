from app.database.repository import search_faqs, get_faqs_by_ids
from app.knowledge.embeddings import embed_texts
from app.knowledge.indexing import client
from app.config.settings import settings

async def retrieve(db, query, category=None, source_id=None, limit=5):
    # Keyword search is always available; semantic results are merged when configured.
    keyword=search_faqs(db,query,category,source_id,limit)
    if not settings.EMBEDDING_PROVIDER or not settings.EMBEDDING_MODEL: return keyword
    try:
        vector=(await embed_texts([query]))[0]; q=client()
        if not q.collection_exists(settings.QDRANT_COLLECTION): return keyword
        from qdrant_client import models
        filt=models.Filter(must=[])
        if category: filt.must.append(models.FieldCondition(key="category",match=models.MatchValue(value=category)))
        if source_id: filt.must.append(models.FieldCondition(key="source_id",match=models.MatchValue(value=str(source_id))))
        res=q.query_points(collection_name=settings.QDRANT_COLLECTION,query=vector,query_filter=filt if filt.must else None,limit=min(max(limit*3,limit),100)).points
        ids=[p.payload.get("faq_id") for p in res if p.payload and p.payload.get("faq_id")]
        if ids:
            by_id=get_faqs_by_ids(db,ids)
            by_id.update({str(x["id"]):x for x in search_faqs(db,query,category,source_id,limit*3)})
            for p in res:
                item=by_id.get(str(p.payload.get("faq_id")))
                if item:
                    item["relevance_score"]=max(float(item.get("relevance_score",0)),float(p.score)); item["matched"]=True
            keyword=sorted(by_id.values(),key=lambda x:x["relevance_score"],reverse=True)[:limit]
    except Exception:
        # Keep retrieval useful when the optional vector service is unavailable.
        pass
    threshold=settings.RELEVANCE_THRESHOLD
    return [r for r in keyword if r["relevance_score"] >= threshold][:limit]
