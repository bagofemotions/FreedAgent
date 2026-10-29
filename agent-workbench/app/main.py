import uuid
from pathlib import Path

from fastapi import FastAPI, BackgroundTasks, HTTPException
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from app.config import settings
from app.providers import configured_providers
from app.store import (
    init_db, create_task, get_task, list_tasks, update_task,
    get_setting, set_setting, dbopen,
)
from app.workflows import run_workflow

app = FastAPI(title="Agent Workbench", version="0.2.0")
WEB = Path(__file__).resolve().parent.parent / "web"


@app.on_event("startup")
def startup():
    init_db()
    Path(settings.workspace_dir).mkdir(parents=True, exist_ok=True)


class TaskRequest(BaseModel):
    mode: str = Field(pattern="^(chat|research|swe)$")
    prompt: str = Field(min_length=1, max_length=30000)


class GatewayKeyRequest(BaseModel):
    api_key: str = Field(min_length=1, max_length=500)


async def execute(task_id, mode, prompt):
    try:
        await run_workflow(task_id, mode, prompt)
    except Exception as exc:
        update_task(
            task_id,
            status="failed",
            error=f"{type(exc).__name__}: {str(exc)[:1500]}",
            checkpoint={"stage": "failed"},
        )


@app.get("/health")
def health():
    return {"status": "ok", "service": "agent-workbench", "version": "0.2.0"}


@app.get("/api/settings")
def get_settings():
    return {
        "gateway": "FreeLLMAPI",
        "api_key_configured": bool(get_setting("freellmapi_api_key")),
    }


@app.post("/api/settings/gateway-key")
def save_gateway_key(req: GatewayKeyRequest):
    set_setting("freellmapi_api_key", req.api_key.strip())
    return {"saved": True, "gateway": "FreeLLMAPI", "api_key_configured": True}


@app.delete("/api/settings/gateway-key")
def clear_gateway_key():
    with dbopen() as db:
        db.execute("DELETE FROM app_settings WHERE key=?", ("freellmapi_api_key",))
    return {"saved": True, "api_key_configured": False}


@app.get("/api/providers")
def providers():
    configured = configured_providers()
    return {
        "providers": configured,
        "configured": bool(configured),
        "gateway": "FreeLLMAPI",
        "hint": None if configured and configured[0].get("has_api_key") else
            "Start FreeLLMAPI, configure a provider, copy its unified API key, and save it in the Model gateway setup panel.",
    }


@app.post("/api/tasks", status_code=202)
async def submit(req: TaskRequest, background_tasks: BackgroundTasks):
    task_id = str(uuid.uuid4())
    create_task(task_id, req.mode, req.prompt)
    background_tasks.add_task(execute, task_id, req.mode, req.prompt)
    return {"task_id": task_id, "status": "queued", "poll_url": f"/api/tasks/{task_id}"}


@app.get("/api/tasks")
def tasks():
    return {"tasks": list_tasks()}


@app.get("/api/tasks/{task_id}")
def task_detail(task_id: str):
    task = get_task(task_id)
    if not task:
        raise HTTPException(404, "Task not found")
    return task


@app.get("/artifacts/{task_id}/{filename}")
def artifact(task_id: str, filename: str):
    if "/" in filename or "\\\\" in filename or filename.startswith("."):
        raise HTTPException(400, "Invalid filename")
    path = Path(settings.data_dir) / "artifacts" / task_id / filename
    if not path.is_file():
        raise HTTPException(404, "Artifact not found")
    return FileResponse(path, filename=filename)


@app.get("/", response_class=HTMLResponse)
def index():
    return (WEB / "index.html").read_text(encoding="utf-8")


app.mount("/static", StaticFiles(directory=str(WEB)), name="static")
