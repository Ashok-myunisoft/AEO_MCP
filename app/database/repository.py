"""SQL access for registry records. All values are bound parameters."""
from __future__ import annotations
import re
import uuid
from sqlalchemy import text
from sqlalchemy.orm import Session
from app.database.connection import SessionLocal


def session_scope():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _row(row):
    return dict(row._mapping) if row else None


def search_faqs(db: Session, query: str, category: str | None = None, source_id: uuid.UUID | None = None, limit: int = 5):
    terms = [x for x in re.findall(r"[\w]+", query.lower()) if len(x) > 1]
    if not terms:
        return []
    # Combine PostgreSQL full text ranking with normalized substring overlap.
    stmt = text("""
      SELECT f.id, f.question, f.answer, f.category, f.metadata, f.language,
             s.id AS source_id, s.source_name, s.source_url,
             ts_rank_cd(to_tsvector('simple', coalesce(f.question,'') || ' ' || coalesce(f.answer,'')), plainto_tsquery('simple', :query)) AS fts_score,
             (SELECT count(*) FROM unnest(CAST(:terms AS text[])) t WHERE
               lower(coalesce(f.normalized_question,f.question,'')) LIKE ('%' || t || '%') OR
               lower(f.answer) LIKE ('%' || t || '%'))::float / :term_count AS overlap
      FROM knowledge_faqs f JOIN knowledge_sources s ON s.id=f.source_id
      WHERE lower(coalesce(f.status,'active')) NOT IN ('deleted','inactive','failed')
        AND (CAST(:category AS text) IS NULL OR lower(coalesce(f.category,s.category,''))=lower(CAST(:category AS text)))
        AND (CAST(:source_id AS uuid) IS NULL OR f.source_id=CAST(:source_id AS uuid))
        AND (to_tsvector('simple', coalesce(f.question,'') || ' ' || coalesce(f.answer,'')) @@ plainto_tsquery('simple', :query)
          OR EXISTS (SELECT 1 FROM unnest(CAST(:terms AS text[])) t WHERE lower(f.question) LIKE ('%' || t || '%') OR lower(f.answer) LIKE ('%' || t || '%')))
      ORDER BY (ts_rank_cd(to_tsvector('simple', coalesce(f.question,'') || ' ' || coalesce(f.answer,'')), plainto_tsquery('simple', :query)) * 0.7 +
        (SELECT count(*) FROM unnest(CAST(:terms AS text[])) t WHERE lower(coalesce(f.normalized_question,f.question,'')) LIKE ('%' || t || '%') OR lower(f.answer) LIKE ('%' || t || '%'))::float / :term_count * 0.3) DESC
      LIMIT :limit
    """)
    rows = db.execute(stmt, {"query":query, "terms":terms, "term_count":len(terms), "category":category, "source_id":str(source_id) if source_id else None, "limit":max(1,min(limit,50))}).mappings().all()
    out=[]
    for r in rows:
        d=dict(r); d["relevance_score"]=float(d.pop("fts_score") or 0)*0.7+float(d.pop("overlap") or 0)*0.3
        d["matched"] = True; out.append(d)
    return out


def get_faq(db: Session, faq_id: uuid.UUID):
    return _row(db.execute(text("SELECT f.*,s.source_name,s.source_url,s.source_type FROM knowledge_faqs f JOIN knowledge_sources s ON s.id=f.source_id WHERE f.id=:id"), {"id":faq_id}).first())


def get_faqs_by_ids(db: Session, ids):
    if not ids: return {}
    rows=db.execute(text("SELECT f.*,s.source_name,s.source_url,s.source_type FROM knowledge_faqs f JOIN knowledge_sources s ON s.id=f.source_id WHERE f.id=ANY(CAST(:ids AS uuid[])) AND lower(coalesce(f.status,'active')) NOT IN ('deleted','inactive','failed')"), {"ids":[str(x) for x in ids]}).mappings().all()
    return {str(r["id"]):dict(r) for r in rows}


def list_sources(db: Session, source_type=None, status=None, category=None):
    rows=db.execute(text("SELECT id,source_name,source_type,source_url,category,description,status,auto_sync,sync_frequency_hours,last_synced_at,metadata,created_at,updated_at FROM knowledge_sources WHERE (CAST(:type AS text) IS NULL OR upper(source_type)=upper(CAST(:type AS text))) AND (CAST(:status AS text) IS NULL OR lower(status)=lower(CAST(:status AS text))) AND (CAST(:category AS text) IS NULL OR lower(coalesce(category,''))=lower(CAST(:category AS text))) ORDER BY source_name"), {"type":source_type,"status":status,"category":category}).mappings().all()
    return [dict(r) for r in rows]


def log_access(db: Session, tool, query=None, faq_id=None, score=None, status="ok", elapsed=0):
    db.execute(text("INSERT INTO mcp_access_logs (id,tool_name,query,matched_faq_id,relevance_score,response_status,execution_time_ms,created_at) VALUES (:id,:tool,:query,:faq,:score,:status,:elapsed,now())"), {"id":uuid.uuid4(),"tool":tool,"query":query,"faq":faq_id,"score":score,"status":status,"elapsed":int(elapsed)})
    db.commit()
