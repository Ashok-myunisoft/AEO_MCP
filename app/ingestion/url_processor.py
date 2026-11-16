import hashlib, uuid
from sqlalchemy import text
from app.database.connection import SessionLocal
from app.ingestion.url_crawler import fetch_url
from app.ingestion.faq_extractor import extract_faqs
from app.knowledge.indexing import index_chunks

async def ingest_url(url: str, source_name: str | None = None, category: str | None = None):
    html=await fetch_url(url); digest=hashlib.sha256(html.encode()).hexdigest(); source_name=source_name or url
    db=SessionLocal(); sid=None
    try:
        sid=db.execute(text("SELECT id FROM knowledge_sources WHERE source_url=:url ORDER BY created_at LIMIT 1"),{"url":url}).scalar()
        if sid is None:
            sid=uuid.uuid4(); db.execute(text("INSERT INTO knowledge_sources(id,source_name,source_type,source_url,category,status,auto_sync,metadata,created_at,updated_at) VALUES(:id,:name,'URL',:url,:category,'ACTIVE',false,'{}',now(),now())"),{"id":sid,"name":source_name,"url":url,"category":category})
        docid=uuid.uuid4(); title=url
        db.execute(text("INSERT INTO knowledge_documents(id,source_id,document_name,document_type,source_url,content_hash,extracted_text,status,metadata,created_at,updated_at) VALUES(:id,:sid,:name,'HTML',:url,:hash,:body,'COMPLETED',CAST(:meta AS jsonb),now(),now())"),{"id":docid,"sid":sid,"name":title,"url":url,"hash":digest,"body":html,"meta":'{"title":"'+title.replace('"','')+'"}'})
        faqs=extract_faqs(html,url); indexed=[]
        for f in faqs:
            h=hashlib.sha256((f['question'].strip()+"\n"+f['answer'].strip()).encode()).hexdigest()
            existing=db.execute(text("SELECT id FROM knowledge_faqs WHERE source_id=:sid AND content_hash=:hash"),{"sid":sid,"hash":h}).scalar()
            fid=existing or uuid.uuid4()
            if existing: db.execute(text("UPDATE knowledge_faqs SET question=:q,answer=:a,category=coalesce(:cat,category),document_id=:doc,metadata=CAST(:meta AS jsonb),updated_at=now() WHERE id=:id"),{"q":f['question'],"a":f['answer'],"cat":category or f['category'],"doc":docid,"meta":'{}',"id":fid})
            else: db.execute(text("INSERT INTO knowledge_faqs(id,source_id,document_id,question,answer,normalized_question,category,language,content_hash,status,metadata,created_at,updated_at) VALUES(:id,:sid,:doc,:q,:a,:n,:cat,'en',:hash,'ACTIVE','{}',now(),now())"),{"id":fid,"sid":sid,"doc":docid,"q":f['question'],"a":f['answer'],"n":f['question'].lower(),"cat":category or f['category'],"hash":h})
            indexed.append({"id":str(fid),"text":f"Question: {f['question']}\nAnswer: {f['answer']}","payload":{"source_id":str(sid),"document_id":str(docid),"faq_id":str(fid),"question":f['question'],"answer":f['answer'],"category":category or f['category'],"source_name":source_name,"source_url":url,"content_type":"faq","language":"en","content_hash":h}})
        db.execute(text("INSERT INTO knowledge_sync_logs(id,source_id,sync_type,status,documents_processed,faqs_extracted,started_at,completed_at) VALUES(:id,:sid,'URL','COMPLETED',1,:count,now(),now())"),{"id":uuid.uuid4(),"sid":sid,"count":len(faqs)}); db.commit()
        try: n=await index_chunks(indexed)
        except RuntimeError: n=0 # ingestion stays usable until embeddings are configured
        return {"source_id":str(sid),"document_id":str(docid),"faqs_extracted":len(faqs),"chunks_indexed":n}
    except Exception as e:
        db.rollback()
        if sid:
            db.execute(text("INSERT INTO knowledge_sync_logs(id,source_id,sync_type,status,error_message,started_at,completed_at) VALUES(:id,:sid,'URL','FAILED',:err,now(),now())"),{"id":uuid.uuid4(),"sid":sid,"err":str(e)[:1000]}); db.commit()
        raise
    finally: db.close()
