import os, subprocess, time
from pathlib import Path
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

WORKSPACE=Path(os.getenv("WORKSPACE_DIR","/workspace")).resolve()
MAX_SECONDS=int(os.getenv("SANDBOX_MAX_SECONDS","120"))
app=FastAPI(title="Sandbox",docs_url=None,redoc_url=None)
class RunRequest(BaseModel):
    command:list[str]=Field(min_length=1,max_length=30)
    timeout_seconds:int=Field(default=60,ge=1,le=120)
    cwd:str="/workspace"
ALLOWED={"pwd","ls","find","cat","git","grep","sed","wc","head","tail","patch"}
@app.get("/health")
def health(): return {"status":"ok"}
@app.post("/run")
def run(req:RunRequest):
    exe=Path(req.command[0]).name
    if exe not in ALLOWED: raise HTTPException(403,"Command not allowed: "+exe)
    if exe == "git" and (len(req.command) < 2 or req.command[1] not in {"status", "apply", "diff", "rev-parse", "log"}):
        raise HTTPException(403, "Git subcommand not allowed")
    if exe == "git" and req.command[1] == "apply" and any(x in req.command for x in ("--unsafe-paths", "--directory")):
        raise HTTPException(403, "Unsafe git apply option")
    cwd=Path(req.cwd).resolve()
    if cwd!=WORKSPACE and WORKSPACE not in cwd.parents: raise HTTPException(400,"cwd must be inside /workspace")
    if not cwd.is_dir(): raise HTTPException(400,"cwd does not exist")
    start=time.time()
    try:
        p=subprocess.run(req.command,cwd=str(cwd),capture_output=True,text=True,timeout=min(req.timeout_seconds,MAX_SECONDS),
          env={"PATH":os.getenv("PATH","/usr/local/bin:/usr/bin:/bin"),"HOME":"/tmp","CI":"1"},check=False)
        return {"exit_code":p.returncode,"stdout":p.stdout[-20000:],"stderr":p.stderr[-20000:],"duration_seconds":round(time.time()-start,2),"timed_out":False}
    except subprocess.TimeoutExpired:
        return {"exit_code":124,"stdout":"","stderr":"Command timed out","duration_seconds":round(time.time()-start,2),"timed_out":True}
if __name__=="__main__":
    import uvicorn; uvicorn.run(app,host="0.0.0.0",port=8090)
