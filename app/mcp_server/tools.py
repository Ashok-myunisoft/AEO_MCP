import logging, time, uuid
from datetime import date, datetime
from app.database.connection import SessionLocal
from app.database.repository import get_faq, list_sources, log_access
from app.knowledge.retrieval import retrieve

logger=logging.getLogger(__name__)

def _jsonable(value):
    if isinstance(value,uuid.UUID): return str(value)
    if isinstance(value,(datetime,date)): return value.isoformat()
    if isinstance(value,dict): return {str(k):_jsonable(v) for k,v in value.items()}
    if isinstance(value,(list,tuple)): return [_jsonable(v) for v in value]
    return value

def _limit(value):
    if isinstance(value,bool) or not isinstance(value,int) or not 1<=value<=50: raise ValueError("limit must be an integer from 1 to 50")
    return value

async def search_faq(query: str, category: str | None=None, source_id: str | None=None, limit: int=5):
    if not isinstance(query,str) or not query.strip() or len(query)>1000: raise ValueError("query must contain 1 to 1000 characters")
    sid=uuid.UUID(source_id) if source_id else None; limit=_limit(limit); db=SessionLocal(); started=time.monotonic()
    try:
        results=await retrieve(db,query.strip(),category,sid,limit)
        log_access(db,"search_faq",query,results[0]["id"] if results else None,results[0]["relevance_score"] if results else None,"matched" if results else "no_match",(time.monotonic()-started)*1000)
        return _jsonable({"matched":bool(results),"results":[{k:r.get(k) for k in ("id","question","answer","source_name","source_url","category","relevance_score")} for r in results]})
    except Exception as e:
        db.rollback(); logger.exception("search_faq failed"); log_access(db,"search_faq",query,status="error",elapsed=(time.monotonic()-started)*1000); raise ValueError("FAQ search failed") from e
    finally: db.close()

def get_faq_answer(faq_id: str):
    fid=uuid.UUID(faq_id); db=SessionLocal()
    try:
        row=get_faq(db,fid); log_access(db,"get_faq_answer",faq_id=fid,status="matched" if row else "no_match")
        if not row: return {"matched":False,"message":"No FAQ found for this ID"}
        return _jsonable({"matched":True,**{k:row.get(k) for k in ("id","question","answer","source_id","source_name","source_url","source_type","category","metadata","language","created_at","updated_at")}})
    finally: db.close()

def list_knowledge_sources(source_type: str | None=None, status: str | None=None, category: str | None=None):
    if source_type and source_type.upper() not in ("URL","DOCUMENT"): raise ValueError("source_type must be URL or DOCUMENT")
    db=SessionLocal()
    try:
        rows=list_sources(db,source_type,status,category); log_access(db,"list_knowledge_sources")
        return _jsonable({"sources":rows,"count":len(rows)})
    finally: db.close()

async def search_by_category(category: str, query: str, limit: int=5):
    if not category or len(category)>120: raise ValueError("category must contain 1 to 120 characters")
    return await search_faq(query,category=category,limit=limit)
