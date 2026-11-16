import hashlib, os, re, uuid, zipfile, io
from pathlib import Path
from sqlalchemy import text
from app.config.settings import settings
from app.database.connection import SessionLocal
from app.ingestion.document_parser import parse_document
from app.knowledge.indexing import index_chunks
from app.knowledge.chunking import chunk_text

def _faq_pairs(rows):
    pairs=[]; pending=None
    for row in rows:
        q=row.get("question"); a=row.get("answer")
        if q and a: pairs.append((q,a)); continue
        t=row["text"].strip()
        m=re.match(r"^(?:Q(?:uestion)?\s*)?\d*[.):-]?\s*(.+?\?)\s*$",t,re.I)
        if m: pending=m.group(1); continue
        m=re.match(r"^(?:A(?:nswer)?\s*[:.)-]\s*)(.+)$",t,re.I)
        if m and pending: pairs.append((pending,m.group(1))); pending=None; continue
        if pending and t: pairs.append((pending,t)); pending=None
    return pairs

async def ingest_document(upload_name: str, content: bytes, category=None):
    ext=Path(upload_name).suffix.lower()
    if ext not in (".pdf",".docx",".xlsx",".txt"): raise ValueError("Unsupported document format")
    if not content or len(content)>settings.MAX_FILE_SIZE_MB*1024*1024: raise ValueError("Empty file or file exceeds configured maximum size")
    if ext==".pdf" and not content.startswith(b"%PDF-"): raise ValueError("File contents do not match PDF format")
    if ext in (".docx",".xlsx"):
        try:
            with zipfile.ZipFile(io.BytesIO(content)) as archive:
                names=set(archive.namelist())
                expected="word/document.xml" if ext==".docx" else "xl/workbook.xml"
                if expected not in names: raise ValueError(f"File contents do not match {ext[1:].upper()} format")
        except zipfile.BadZipFile as e: raise ValueError("Office document is not a valid ZIP container") from e
    if ext==".txt" and b"\x00" in content[:4096]: raise ValueError("TXT file contains binary data")
    digest=hashlib.sha256(content).hexdigest(); root=Path(settings.UPLOAD_DIR).resolve(); root.mkdir(parents=True,exist_ok=True)
    db=SessionLocal()
    try:
        existing=db.execute(text("SELECT id FROM knowledge_documents WHERE content_hash=:hash"),{"hash":digest}).scalar()
        if existing: return {"document_id":str(existing),"duplicate":True}
        docid=uuid.uuid4(); path=root/f"{docid}{ext}"; path.write_bytes(content)
        rows=parse_document(path); extracted="\n".join(r["text"] for r in rows)
        if not extracted.strip(): raise ValueError("No readable text found in document")
        sourceid=uuid.uuid4(); db.execute(text("INSERT INTO knowledge_sources(id,source_name,source_type,category,status,metadata,created_at,updated_at) VALUES(:id,:name,'DOCUMENT',:cat,'ACTIVE','{}',now(),now())"),{"id":sourceid,"name":Path(upload_name).name,"cat":category})
        outdir=Path(settings.EXTRACTED_DIR); outdir.mkdir(parents=True,exist_ok=True); extracted_path=outdir/f"{docid}.txt"; extracted_path.write_text(extracted,encoding="utf-8")
        db.execute(text("INSERT INTO knowledge_documents(id,source_id,document_name,document_type,file_path,content_hash,extracted_text,status,metadata,created_at,updated_at) VALUES(:id,:sid,:name,:type,:path,:hash,:body,'COMPLETED',CAST(:meta AS jsonb),now(),now())"),{"id":docid,"sid":sourceid,"name":Path(upload_name).name,"type":ext[1:].upper(),"path":str(path),"hash":digest,"body":extracted,"meta":'{"extracted_path":"'+str(extracted_path).replace('\\','/')+'"}'})
        pairs=_faq_pairs(rows); batch=[]
        for q,a in pairs:
            h=hashlib.sha256((q+"\n"+a).encode()).hexdigest(); fid=uuid.uuid4()
            db.execute(text("INSERT INTO knowledge_faqs(id,source_id,document_id,question,answer,normalized_question,category,language,content_hash,status,metadata,created_at,updated_at) VALUES(:id,:sid,:did,:q,:a,:n,:cat,'en',:hash,'ACTIVE','{}',now(),now())"),{"id":fid,"sid":sourceid,"did":docid,"q":q,"a":a,"n":q.lower(),"cat":category,"hash":h})
            batch.append({"id":str(fid),"text":f"Question: {q}\nAnswer: {a}","payload":{"source_id":str(sourceid),"document_id":str(docid),"faq_id":str(fid),"question":q,"answer":a,"category":category,"source_name":Path(upload_name).name,"source_url":None,"content_type":"faq","language":"en","content_hash":h}})
        if not pairs:
            for index,chunk in enumerate(chunk_text(extracted)):
                batch.append({"id":f"{docid}:{index}","text":chunk,"payload":{"source_id":str(sourceid),"document_id":str(docid),"faq_id":None,"category":category,"source_name":Path(upload_name).name,"source_url":None,"content_type":"document","language":"en","content_hash":digest,"chunk_index":index}})
        db.execute(text("INSERT INTO knowledge_sync_logs(id,source_id,sync_type,status,documents_processed,faqs_extracted,started_at,completed_at) VALUES(:id,:sid,'DOCUMENT','COMPLETED',1,:n,now(),now())"),{"id":uuid.uuid4(),"sid":sourceid,"n":len(pairs)}); db.commit()
        indexed=await index_chunks(batch) if batch else 0
        return {"source_id":str(sourceid),"document_id":str(docid),"faqs_extracted":len(pairs),"chunks_indexed":indexed,"status":"processed"}
    except Exception:
        db.rollback(); raise
    finally: db.close()
