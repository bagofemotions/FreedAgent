#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"
MODE="${1:-setup}"

if ! command -v docker >/dev/null 2>&1; then
  echo "Docker is required. Install Docker Engine/Desktop and the Compose plugin first." >&2
  exit 1
fi
if ! docker compose version >/dev/null 2>&1; then
  echo "Docker Compose plugin is required (docker compose)." >&2
  exit 1
fi

if [[ ! -f .env ]]; then
  if command -v openssl >/dev/null 2>&1; then
    ENC_KEY="$(openssl rand -hex 32)"
  else
    ENC_KEY="$(python3 -c 'import secrets; print(secrets.token_hex(32))')"
  fi
  cat > .env <<EOF
HOST_PORT=8080
FREEAPI_HOST_PORT=3001
ENCRYPTION_KEY=${ENC_KEY}
MODEL_PROVIDERS=free
MODEL_FREE_BASE_URL=http://freellmapi:3001/v1
MODEL_FREE_API_KEY=
MODEL_FREE_MODEL=auto
MODEL_TIMEOUT_SECONDS=60
MAX_MODEL_ATTEMPTS=3
RESEARCH_MAX_BYTES=1500000
SANDBOX_MAX_SECONDS=120
EOF
  chmod 600 .env
  echo "Created .env and generated a persistent FreeLLMAPI encryption key."
fi

if [[ "$MODE" == "--connect" ]]; then
  printf "Paste the unified FreeLLMAPI API key from its dashboard (input hidden): "
  IFS= read -r -s FREE_KEY
  echo
  if [[ -z "$FREE_KEY" ]]; then
    echo "No key entered; leaving configuration unchanged." >&2
    exit 2
  fi
  python3 - "$FREE_KEY" <<'PY'
from pathlib import Path
import sys
p = Path(".env")
key = sys.argv[1]
lines = p.read_text(encoding="utf-8").splitlines()
out = []
seen = False
for line in lines:
    if line.startswith("MODEL_FREE_API_KEY="):
        out.append("MODEL_FREE_API_KEY=" + key)
        seen = True
    else:
        out.append(line)
if not seen:
    out.append("MODEL_FREE_API_KEY=" + key)
p.write_text("\n".join(out) + "\n", encoding="utf-8")
p.chmod(0o600)
PY
  echo "Saved gateway key to .env (file permissions restricted)."
  docker compose build api sandbox
  docker compose up -d
  echo
  echo "Workbench started. Open http://localhost:${HOST_PORT:-8080}"
  exit 0
fi

docker compose pull freellmapi
docker compose up -d freellmapi
echo
echo "FreeLLMAPI is starting."
echo "1. Open http://localhost:${FREEAPI_HOST_PORT:-3001}"
echo "2. In FreeLLMAPI, configure at least one provider/model (use a free-tier provider if available)."
echo "3. Copy the unified API key from the FreeLLMAPI dashboard."
echo "4. Run: ./setup.sh --connect"
echo
echo "Provider API credentials are configured in FreeLLMAPI's own dashboard, not in this project's .env."
echo "A provider may still require its own API key; free model availability and quotas are not guaranteed."
