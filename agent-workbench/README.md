# Agent Workbench — prototype v0.2

Open-source-first Docker Compose starter for three modes: chat, research/document generation, and software engineering. It includes FreeLLMAPI as the default swappable model gateway, with optional paid-provider fallback configured in the gateway UI.

## Quick start — no provider configuration in the workbench .env

Prerequisites: Docker with Compose v2. Internet access is needed to pull images and use hosted model providers.

```bash
./start.sh
```

The script generates a random FreeLLMAPI encryption key in a local `.env` file if one does not exist, then builds and starts the services. You do not have to edit `.env` or enter model URLs/model IDs manually.

Open:
- Agent Workbench: http://localhost:8080
- FreeLLMAPI dashboard: http://localhost:3001

In FreeLLMAPI, configure at least one provider. Copy its unified API key from the dashboard and paste it into the **Model gateway setup** panel in Agent Workbench. This is a one-time credential connection, not manual provider configuration. Free hosted providers may still require provider-specific registration or keys, and free quotas/availability vary.

## CLI

```bash
./agent chat "Explain dependency injection simply"
./agent research "Compare these sources https://example.com https://www.iana.org/domains/reserved"
./agent swe "Fix the validation bug in this repository"
```

For SWE, put a Git repository under `./workspace` first.

## Architecture

- FastAPI API, browser UI, and CLI wrapper.
- FreeLLMAPI service (`ghcr.io/tashfeenahmed/freellmapi:latest`) for provider configuration, routing and unified OpenAI-compatible API.
- Persistent SQLite task state and gateway-key configuration in the `agent_data` volume.
- Separate sandbox container with a small command allowlist and resource limits.
- Research and SWE artifact ZIPs with verification reports.

FreeLLMAPI is treated as a replaceable gateway rather than being coupled to the orchestration code. The workbench uses its OpenAI-compatible `/v1/chat/completions` endpoint.

## Tests

```bash
pip install -r requirements.txt
pytest -q
```

Docker and end-to-end provider calls must still be verified on the target host. This repository's files have not been represented as Docker-tested unless you run the build and checks yourself.

## Prototype limitations

- This is not production-ready and does not claim production readiness.
- API has no authentication. Bind it to localhost or put it behind an authenticated reverse proxy before sharing it.
- FreeLLMAPI is a single-user gateway and its dashboard/API should not be exposed to untrusted networks. The Compose configuration binds its UI to loopback by default.
- The gateway's unified API key is stored in the workbench's SQLite volume. Protect Docker volumes and host access; this prototype does not encrypt that stored token independently.
- The sandbox is constrained but not a hardened hostile-code sandbox. Do not expose it or mount the Docker socket.
- Host execution is not implemented.
- Research only fetches URLs explicitly supplied in the prompt; citations are not independently verified.
- SWE proposes a plan and unified diff, validates with `git apply --check`, and records status. It does not yet run project-specific build/test recipes or package the full modified application.
- Task records/checkpoints persist, but interrupted tasks are not automatically resumed by a durable queue worker.
- URL checks reduce SSRF risk but do not cover every DNS rebinding or redirect scenario.
- Free providers can change availability, impose quotas, require registration, or disappear.
- Do not commit `.env`, provider credentials, private source, or secrets.

## Next production-hardening steps

Add authentication and authorization; durable queue/restart recovery; per-task ephemeral sandboxes and strict network egress; project-specific test/build plans; complete source packaging and checksums; robust search/extraction and claim-level citation verification; image/dependency pinning, SBOM, and CI.
