import json, re
from bs4 import BeautifulSoup

def extract_faqs(html: str, page_url: str):
    soup=BeautifulSoup(html,"lxml"); title=soup.title.get_text(" ",strip=True) if soup.title else ""
    category=" ".join(x for x in [soup.find("meta",property="article:section").get("content") if soup.find("meta",property="article:section") else "", title] if x)[:150] or None
    found=[]
    for script in soup.select('script[type="application/ld+json"]'):
        try: data=json.loads(script.string or script.get_text())
        except Exception: continue
        stack=data if isinstance(data,list) else [data]
        while stack:
            item=stack.pop()
            if isinstance(item,dict):
                typ=item.get("@type",[]); typ=[typ] if isinstance(typ,str) else typ
                if "FAQPage" in typ:
                    for entity in item.get("mainEntity",[]):
                        ans=entity.get("acceptedAnswer",{}) if isinstance(entity,dict) else {}
                        q=entity.get("name","").strip(); a=ans.get("text","").strip() if isinstance(ans,dict) else ""
                        if q and a: found.append({"question":BeautifulSoup(q,"lxml").get_text(" ",strip=True),"answer":BeautifulSoup(a,"lxml").get_text(" ",strip=True),"category":category,"source_url":page_url,"metadata":{"page_title":title,"extractor":"jsonld"}})
                stack.extend(v for v in item.values() if isinstance(v,(dict,list)))
            elif isinstance(item,list): stack.extend(item)
    if found: return found
    for tag in soup(["script","style","nav","header","footer","aside","noscript"]): tag.decompose()
    root=soup.find("main") or soup.find("article") or soup.body or soup
    # Common accordion/question-answer structures first.
    for el in root.select("details"):
        q=el.find("summary"); a=el
        if q:
            answer=a.get_text(" ",strip=True).replace(q.get_text(" ",strip=True),"",1).strip()
            if answer: found.append((q.get_text(" ",strip=True),answer))
    if not found:
        for q in root.select("h2,h3,h4,[class*=question],[class*=faq-question]"):
            question=q.get_text(" ",strip=True)
            if len(question)<8 or not question.endswith(("?","？")): continue
            bits=[]; sibling=q.find_next_sibling()
            while sibling and sibling.name not in ("h1","h2","h3","h4") and len(bits)<8:
                t=sibling.get_text(" ",strip=True)
                if t: bits.append(t)
                sibling=sibling.find_next_sibling()
            answer=" ".join(bits).strip()
            if answer: found.append((question,answer))
    output=[]
    seen=set()
    for q,a in found:
        if isinstance(q,dict): output.append(q); continue
        if q.lower() not in seen:
            seen.add(q.lower()); output.append({"question":q,"answer":a,"category":category,"source_url":page_url,"metadata":{"page_title":title,"extractor":"dom"}})
    return output
