from docx import Document
def parse_docx(path):
    d=Document(path); out=[]
    for p in d.paragraphs:
        if p.text.strip(): out.append({"text":p.text.strip(),"reference":"paragraph"})
    for ti,t in enumerate(d.tables):
        for ri,row in enumerate(t.rows):
            vals=[c.text.strip() for c in row.cells]
            if any(vals): out.append({"text":" | ".join(vals),"reference":f"table {ti+1}, row {ri+1}"})
    return out
