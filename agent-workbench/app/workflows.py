import json, re, uuid, zipfile
from pathlib import Path
import httpx
from app.config import settings
from app.providers import chat
from app.research import fetch_sources
from app.store import update_task

CHAT_SYS="You are a helpful assistant. Be accurate and explicit about uncertainty."
RESEARCH_SYS="You are a careful research analyst. Use only supplied excerpts as evidence. Cite claims as [S1], [S2]. Never invent citations. Include limitations and a source list."
SWE_SYS="You are a cautious software engineer. Make the smallest change. Never claim tests passed without output. When asked to edit, return a unified diff in one ```diff block."

async def sandbox(command, cwd="/workspace", timeout=60):
    async with httpx.AsyncClient(timeout=timeout+5) as c:
        r=await c.post(settings.sandbox_url+"/run",json={"command":command,"cwd":cwd,"timeout_seconds":timeout})
        r.raise_for_status(); return r.json()

def write_zip(outdir, name, files):
    outdir.mkdir(parents=True,exist_ok=True); zp=outdir/name
    with zipfile.ZipFile(zp,"w",zipfile.ZIP_DEFLATED) as z:
        for path,arc in files: z.write(path,arc)
    return zp

async def run_workflow(task_id,mode,prompt):
    update_task(task_id,status="running",checkpoint={"stage":"started","mode":mode})
    if mode=="chat":
        r=await chat([{"role":"user","content":prompt}],system=CHAT_SYS)
        result={"answer":r["content"],"provider":r["provider"],"model":r["model"]}
        update_task(task_id,status="completed",checkpoint={"stage":"completed"},result=result); return result
    outdir=Path(settings.data_dir)/"artifacts"/task_id; outdir.mkdir(parents=True,exist_ok=True)
    if mode=="research":
        urls=re.findall(r"https?://[^\s<>\]\)\"']+",prompt)
        sources=await fetch_sources(urls)
        ctx="\n\n".join(f"[S{i}] TITLE: {s['title']}\nURL: {s['url']}\nEXCERPT: {s['text'][:10000]}" for i,s in enumerate(sources,1))
        if not ctx: ctx="No source URLs supplied. Explain that evidence gathering is incomplete; do not invent sources."
        update_task(task_id,checkpoint={"stage":"sources_fetched","count":len(sources)})
        r=await chat([{"role":"user","content":f"Research request:\n{prompt}\n\nSources:\n{ctx}\n\nWrite a structured Markdown report with summary, findings, caveats and source list."}],system=RESEARCH_SYS)
        report=outdir/"research-report.md"; report.write_text(r["content"],encoding="utf-8")
        vr=outdir/"verification-report.json"; vr.write_text(json.dumps({"task_id":task_id,"mode":mode,"sources":[{"label":f"S{i}","url":s["url"],"title":s["title"]} for i,s in enumerate(sources,1)],"note":"Citation correctness has not been independently verified."},indent=2),encoding="utf-8")
        zp=write_zip(outdir,"research-artifacts.zip",[(report,"research-report.md"),(vr,"verification-report.json")])
        result={"report_markdown":r["content"],"provider":r["provider"],"model":r["model"],"source_count":len(sources),"artifact_zip":f"/artifacts/{task_id}/{zp.name}","verification_report":f"/artifacts/{task_id}/{vr.name}"}
        update_task(task_id,status="completed",checkpoint={"stage":"completed"},result=result); return result
    if mode=="swe":
        root=Path(settings.workspace_dir).resolve()
        ignored={".git","node_modules",".venv","venv","dist","build","__pycache__",".env"}
        snippets=[]; total=0
        for p in root.rglob("*"):
            if not p.is_file() or any(x in ignored for x in p.parts): continue
            try:
                if p.stat().st_size>80000: continue
                txt=p.read_text(encoding="utf-8")
            except (UnicodeDecodeError,OSError): continue
            snippets.append(f"\n--- FILE: {p.relative_to(root)} ---\n{txt[:5000]}"); total+=len(txt)
            if total>30000: break
        snapshot="".join(snippets) or "[Workspace is empty]"
        plan=await chat([{"role":"user","content":f"Task: {prompt}\nWorkspace snapshot:\n{snapshot}\nProvide a concise plan and validation approach. Do not edit yet."}],system=SWE_SYS)
        update_task(task_id,checkpoint={"stage":"plan_created","plan":plan["content"][:5000]})
        edit=await chat([{"role":"user","content":f"Task: {prompt}\nWorkspace snapshot:\n{snapshot}\nPlan:\n{plan['content']}\nReturn smallest applicable unified diff in one ```diff block. Use paths relative to repository root."}],system=SWE_SYS)
        m=re.search(r"```diff\s*(.*?)```",edit["content"],re.S|re.I); diff=(m.group(1).strip()+"\n") if m else None
        patch=outdir/"proposed.patch"; report=outdir/"verification-report.json"
        applied=False; patch_check={"exit_code":2,"stderr":"No unified diff found; no patch applied"}
        if diff:
            patch.write_text(diff,encoding="utf-8")
            check=await sandbox(["git","apply","--check",str(patch)])
            if check["exit_code"]==0:
                patch_check=await sandbox(["git","apply",str(patch)])
                applied=patch_check["exit_code"]==0
            else: patch_check=check
        status=await sandbox(["git","status","--short"])
        data={"task_id":task_id,"mode":"swe","task":prompt,"plan":plan["content"],"patch_applied":applied,"patch_result":patch_check,"workspace_status":status,"production_ready":False,"note":"Only Git patch validation and status were run; project-specific build/tests have not been executed."}
        report.write_text(json.dumps(data,indent=2),encoding="utf-8")
        files=[(report,"verification-report.json")]
        if diff: files.append((patch,"proposed.patch"))
        zp=write_zip(outdir,"swe-artifacts.zip",files)
        result={"plan":plan["content"],"patch_generated":bool(diff),"patch_applied":applied,"production_ready":False,"verification_report":f"/artifacts/{task_id}/{report.name}","artifact_zip":f"/artifacts/{task_id}/{zp.name}","note":data["note"]}
        update_task(task_id,status="completed" if applied else "needs_review",checkpoint={"stage":"review_required"},result=result); return result
    raise ValueError("Unknown mode")
