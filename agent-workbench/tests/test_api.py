import os
os.environ["DATA_DIR"]="/tmp/agent-workbench-test-data"
from fastapi.testclient import TestClient
from app.main import app
client=TestClient(app)
def test_health():
    r=client.get("/health"); assert r.status_code==200 and r.json()["status"]=="ok"
def test_ui():
    r=client.get("/"); assert r.status_code==200 and "Agent Workbench" in r.text
def test_invalid_mode():
    r=client.post("/api/tasks",json={"mode":"invalid","prompt":"hi"}); assert r.status_code==422
def test_provider_shape():
    r=client.get("/api/providers"); assert r.status_code==200 and "providers" in r.json()
