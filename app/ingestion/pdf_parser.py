import pymupdf as fitz
def parse_pdf(path):
    doc=fitz.open(path)
    try: return [{"text":p.get_text("text"),"reference":f"page {i+1}"} for i,p in enumerate(doc) if p.get_text("text").strip()]
    finally: doc.close()
