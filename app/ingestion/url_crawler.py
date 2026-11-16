from urllib.parse import urlparse
import ipaddress, socket, asyncio, httpx
from urllib.robotparser import RobotFileParser

def validate_public_url(url):
    p=urlparse(url)
    if p.scheme not in ("http","https") or not p.hostname or p.username or p.password: raise ValueError("Only public http/https URLs are allowed")
    try:
        for result in socket.getaddrinfo(p.hostname,None):
            ip=ipaddress.ip_address(result[4][0])
            if not ip.is_global: raise ValueError("Private or non-public network addresses are blocked")
    except socket.gaierror as e: raise ValueError("URL hostname could not be resolved") from e
    return url

async def fetch_url(url, timeout=20):
    url=validate_public_url(url)
    async with httpx.AsyncClient(timeout=timeout,follow_redirects=False,headers={"User-Agent":"GoodBooksKnowledgeBot/1.0"}) as c:
        robots_url=f"{urlparse(url).scheme}://{urlparse(url).netloc}/robots.txt"
        try:
            rr=await c.get(robots_url); rp=RobotFileParser(robots_url); rp.parse(rr.text.splitlines() if rr.status_code==200 else [])
            if not rp.can_fetch("GoodBooksKnowledgeBot",url): raise PermissionError("robots.txt disallows crawling this URL")
        except httpx.HTTPError: pass
        for attempt in range(3):
            try:
                r=await c.get(url); r.raise_for_status()
                if "html" not in r.headers.get("content-type","").lower(): raise ValueError("URL did not return HTML")
                return r.text
            except httpx.HTTPError:
                if attempt==2: raise
                await asyncio.sleep(.25*(attempt+1))
