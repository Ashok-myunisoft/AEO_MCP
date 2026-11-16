from openpyxl import load_workbook
def parse_xlsx(path):
    w=load_workbook(path,read_only=True,data_only=True); out=[]
    try:
        for s in w.worksheets:
            rows=[[str(c).strip() if c is not None else "" for c in row] for row in s.iter_rows(values_only=True)]
            header=[x.lower() for x in rows[0]] if rows else []
            qi=next((i for i,x in enumerate(header) if x in ("question","faq","questions")),None); ai=next((i for i,x in enumerate(header) if x in ("answer","answers","response")),None)
            for ri,row in enumerate(rows):
                vals=" | ".join(x for x in row if x)
                if vals: out.append({"text":vals,"reference":f"sheet {s.title}, row {ri+1}","question":row[qi] if qi is not None and ri>0 and qi<len(row) else None,"answer":row[ai] if ai is not None and ri>0 and ai<len(row) else None,"sheet":s.title})
    finally: w.close()
    return out
