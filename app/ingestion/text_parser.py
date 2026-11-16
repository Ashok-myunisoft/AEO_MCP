def parse_txt(path):
    with open(path,"r",encoding="utf-8-sig",errors="replace") as f: return [{"text":f.read(),"reference":"text"}]
