import ipaddress, socket, re
from urllib.parse import urlparse
import httpx
from app.config import settings

def validate_url(url):
    p=urlparse(url)
    if p.scheme not in ("http","https") or not p.hostname: raise ValueError("Only absolute HTTP(S) URLs allowed")
    if p.hostname.lower() in ("localhost","localhost.localdomain"): raise ValueError("Local URLs blocked")
    try:
        for info in socket.getaddrinfo(p.hostname,p.port or (443 if p.scheme=="https" else 80)):
            if not ipaddress.ip_address(info[4][0]).is_global: raise ValueError("Non-public destination blocked")
    except socket.gaierror as e: raise ValueError("Could not resolve source host") from e
    return url

async def fetch_sources(urls):
    out=[]
    async with httpx.AsyncClient(timeout=15,follow_redirects=False,headers={"User-Agent":"AgentWorkbench/0.1"}) as client:
        for url in urls[:8]:
            try:
                validate_url(url); r=await client.get(url); r.raise_for_status()
                ct=r.headers.get("content-type","")
                if "text/html" not in ct and "text/plain" not in ct:
                    out.append({"url":url,"title":url,"text":"[Skipped non-text source]"}); continue
                body=r.text[:settings.research_max_bytes]
                m=re.search(r"<title[^>]*>(.*?)</title>",body,re.I|re.S)
                title=re.sub(r"\s+"," ",m.group(1)).strip() if m else url
                body=re.sub(r"(?is)<(script|style|noscript).*?>.*?</\1>"," ",body)
                text=re.sub(r"(?s)<[^>]+>"," ",body)
                text=re.sub(r"\s+"," ",text).strip()
                out.append({"url":url,"title":title[:250],"text":text[:16000]})
            except Exception as e: out.append({"url":url,"title":url,"text":f"[Retrieval failed: {type(e).__name__}: {e}]"})
    return out
