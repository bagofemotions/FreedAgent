import json, os, sqlite3
from datetime import datetime, timezone
from app.config import settings

def stamp():
    return datetime.now(timezone.utc).isoformat()

def dbopen():
    os.makedirs(settings.data_dir, exist_ok=True)
    db = sqlite3.connect(os.path.join(settings.data_dir, "tasks.sqlite3"), timeout=10)
    db.row_factory = sqlite3.Row
    return db

def init_db():
    with dbopen() as db:
        db.execute("CREATE TABLE IF NOT EXISTS app_settings (key TEXT PRIMARY KEY, value TEXT NOT NULL)")
        db.execute('''CREATE TABLE IF NOT EXISTS tasks (
        id TEXT PRIMARY KEY, mode TEXT NOT NULL, prompt TEXT NOT NULL, status TEXT NOT NULL,
        created_at TEXT NOT NULL, updated_at TEXT NOT NULL, checkpoint TEXT NOT NULL,
        result TEXT, error TEXT)''')

def create_task(task_id, mode, prompt):
    t = stamp()
    with dbopen() as db:
        db.execute("INSERT INTO tasks VALUES(?,?,?,?,?,?,?,?,?)",
          (task_id, mode, prompt, "queued", t, t, json.dumps({"stage":"queued"}), None, None))
    return get_task(task_id)

def update_task(task_id, **fields):
    allowed = {"status", "checkpoint", "result", "error"}
    sets, vals = [], []
    for k,v in fields.items():
        if k not in allowed: raise ValueError("Invalid field")
        if k in ("checkpoint","result") and v is not None and not isinstance(v,str):
            v = json.dumps(v, ensure_ascii=False)
        sets.append(k+"=?"); vals.append(v)
    sets.append("updated_at=?"); vals += [stamp(), task_id]
    with dbopen() as db: db.execute("UPDATE tasks SET "+",".join(sets)+" WHERE id=?", vals)

def get_task(task_id):
    with dbopen() as db: row = db.execute("SELECT * FROM tasks WHERE id=?", (task_id,)).fetchone()
    if not row: return None
    item = dict(row)
    for k in ("checkpoint","result"):
        if item[k]:
            try: item[k] = json.loads(item[k])
            except ValueError: pass
    return item

def list_tasks():
    with dbopen() as db: ids = [r["id"] for r in db.execute("SELECT id FROM tasks ORDER BY created_at DESC LIMIT 50")]
    return [get_task(i) for i in ids]


def get_setting(key):
    with dbopen() as db:
        row = db.execute("SELECT value FROM app_settings WHERE key=?", (key,)).fetchone()
    return row["value"] if row else None

def set_setting(key, value):
    with dbopen() as db:
        db.execute("INSERT INTO app_settings(key,value) VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value", (key, value))
