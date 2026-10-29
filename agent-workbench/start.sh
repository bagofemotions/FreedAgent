#!/usr/bin/env sh
set -eu
cd "$(dirname "$0")"
if [ ! -f .env ]; then
  if command -v openssl >/dev/null 2>&1; then
    KEY="$(openssl rand -hex 32)"
  elif command -v python3 >/dev/null 2>&1; then
    KEY="$(python3 -c 'import secrets; print(secrets.token_hex(32))')"
  else
    echo "Need openssl or python3 to generate the FreeLLMAPI encryption key." >&2
    exit 1
  fi
  umask 077
  printf 'ENCRYPTION_KEY=%s\nHOST_PORT=8080\nFREELLMAPI_PORT=3001\n' "$KEY" > .env
  echo "Generated local .env with a random FreeLLMAPI encryption key."
fi
docker compose up --build -d
echo
echo "Agent Workbench: http://localhost:8080"
echo "FreeLLMAPI dashboard: http://localhost:3001"
echo "Next: configure a provider in FreeLLMAPI, copy its unified API key, and paste it into Agent Workbench settings."
