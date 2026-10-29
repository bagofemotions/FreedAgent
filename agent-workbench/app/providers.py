import os, httpx
from app.config import settings
from app.store import get_setting

class ProviderError(RuntimeError): pass

def provider_config(pid):
    prefix = "MODEL_" + pid.upper() + "_"
    if pid.lower() == "free":
        base = os.getenv(prefix+"BASE_URL", os.getenv("FREELLMAPI_BASE_URL", "http://freellmapi:3001/v1")).strip().rstrip("/")
        key = get_setting("freellmapi_api_key") or os.getenv(prefix+"API_KEY", "").strip()
        model = os.getenv(prefix+"MODEL", "auto").strip() or "auto"
        return (base,key,model) if base else None
    base = os.getenv(prefix+"BASE_URL","").strip().rstrip("/")
    key = os.getenv(prefix+"API_KEY","").strip()
    model = os.getenv(prefix+"MODEL","").strip()
    return (base,key,model) if base and model else None

def configured_providers():
    return [{"id":p,"model":c[2],"base_url":c[0],"has_api_key":bool(c[1])} for p in settings.providers if (c:=provider_config(p))]

async def chat(messages, system=None):
    provider_ids = list(settings.providers) or ["free"]
    errors=[]; attempts=0
    for pid in provider_ids:
        if attempts >= settings.max_attempts: break
        cfg=provider_config(pid)
        if not cfg:
            errors.append(pid+": missing base URL or model"); continue
        base,key,model=cfg; attempts += 1
        msgs=([{"role":"system","content":system}] if system else [])+messages
        headers={"Content-Type":"application/json"}
        if key: headers["Authorization"]="Bearer "+key
        try:
            async with httpx.AsyncClient(timeout=settings.timeout) as client:
                r=await client.post(base+"/chat/completions",headers=headers,json={"model":model,"messages":msgs,"temperature":0.2})
                r.raise_for_status(); data=r.json()
                return {"content":data["choices"][0]["message"]["content"],"provider":pid,"model":model,"usage":data.get("usage")}
        except Exception as e: errors.append(f"{pid}: {type(e).__name__}: {str(e)[:200]}")
    raise ProviderError("All configured provider attempts failed: "+" | ".join(errors))
