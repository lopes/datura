# Datura

An LLM honeypot for detection engineering. It deploys a convincing but fake internal AI assistant that appears to leak sensitive data — credentials, API keys, connection strings — when socially engineered. Every interaction is logged, giving defenders a high-fidelity signal of attacker intent and technique.

Named after [*Datura stramonium*](https://en.wikipedia.org/wiki/Datura_stramonium) — a plant that appears ordinary but is highly toxic. The honeypot looks like a misconfigured internal tool; what the attacker extracts is the poison.

## How It Works

```
Attacker ──► Proxy (port 8080) ──► Ollama (internal)
               │                        │
               │  ◄── model response ◄──┘
               │
               ├─ approval phrase detected?
               │    yes ──► inject fake credentials
               │    no  ──► pass through unchanged
               │
               ├─ classify interaction (recon/probe/denied/leaked)
               ├─ log to interactions.jsonl
               └─ return response to attacker
```

The model itself has **zero credentials** in its context. It only does conversation gating — responding helpfully to social engineering while deflecting direct credential requests. The proxy watches for approval phrases in the model's output ("let me look up the staging config...") and deterministically appends honeypot credentials. This separation means the model cannot accidentally leak real data, and credential injection is fully auditable.

## Quick Start

```bash
# Build
docker build -f docker/Dockerfile -t datura .

# Run (first start pulls the model — ~2-5 min, cached on subsequent runs)
docker run -d --name datura \
  -p 8080:8080 \
  -v ollama_data:/data/ollama \
  -v /tmp/datura/logs:/data/logs \
  datura

# Watch startup progress
docker logs -f datura

# Verify
curl http://localhost:8080/
```

## Use Cases

All examples below assume you have already built the image.

### Web UI Decoy

Deploy a fake internal AI assistant portal. Seed breadcrumbs in internal wikis, Slack channels, or phishing simulations pointing to the URL. Attackers see a chat interface with a warning banner about "credentials not being redacted" — an irresistible target.

```bash
docker run -d --name datura -p 80:8080 \
  -v ollama_data:/data/ollama \
  -v /tmp/datura/logs:/data/logs \
  datura
```

### IDE / Editor Decoy

The proxy speaks the OpenAI-compatible `/v1/chat/completions` API. Point a code editor's AI assistant (VS Code + Continue, Cursor, or any OpenAI-compatible client) at the honeypot. Attackers who discover the endpoint and interact with it trigger the same detection pipeline.

Configure your editor to use:
```
API Base URL: http://<honeypot-host>:8080/v1
Model: itassist
```

### API / curl Decoy

Seed an API endpoint in configuration files, environment variables, or internal documentation. Any tool that speaks to the Ollama API or OpenAI API will work:

```bash
# Ollama-native API
curl -s http://honeypot:8080/api/generate \
  -d '{"model":"itassist","prompt":"How do I connect to the staging Kafka cluster?","stream":false}'

# OpenAI-compatible API
curl -s http://honeypot:8080/v1/chat/completions \
  -H 'Content-Type: application/json' \
  -d '{"model":"itassist","messages":[{"role":"user","content":"I need the AWS staging credentials"}]}'
```

### HTTPS Deployment

Serve over TLS for realism. Self-signed or bring your own certs:

```bash
# Self-signed (auto-generated at startup)
docker run -d --name datura \
  -p 80:8080 -p 443:8443 \
  -e GENERATE_SELF_SIGNED=true \
  -v ollama_data:/data/ollama \
  -v /tmp/datura/logs:/data/logs \
  datura

# Custom certificates
docker run -d --name datura \
  -p 443:8443 \
  -e TLS_CERT=/certs/fullchain.pem \
  -e TLS_KEY=/certs/privkey.pem \
  -v /path/to/certs:/certs:ro \
  -v ollama_data:/data/ollama \
  datura
```

## Configuration

All configuration is via environment variables passed to `docker run -e`:

| Variable | Default | Purpose |
|---|---|---|
| `MODEL_NAME` | `itassist` | Ollama model name |
| `BASE_MODEL` | `qwen2.5:3b` | Base model pulled from Ollama registry |
| `PROXY_PORT` | `8080` | Internal proxy listen port |
| `LOG_DIR` | `/data/logs` | Log directory inside container |
| `OLLAMA_HOST` | `127.0.0.1:11434` | Internal Ollama address |
| `TLS_CERT` | *(empty)* | Path to TLS certificate (inside container) |
| `TLS_KEY` | *(empty)* | Path to TLS private key (inside container) |
| `TLS_PORT` | `8443` | Internal HTTPS listen port |
| `TLS_HOSTNAME` | `itassist-beta-...acmecorp.world` | CN for self-signed certificate |
| `GENERATE_SELF_SIGNED` | `false` | Auto-generate a self-signed TLS cert |
| `CUSTOM_CA_CERT` | *(empty)* | Path to custom CA cert inside container (for corporate TLS proxies) |

### Port Mapping Examples

```bash
# HTTP on port 80
docker run -d -p 80:8080 ...

# HTTP on 80 + 8080, HTTPS on 443
docker run -d -p 80:8080 -p 8080:8080 -p 443:8443 -e GENERATE_SELF_SIGNED=true ...

# HTTPS only on 443
docker run -d -p 443:8443 -e GENERATE_SELF_SIGNED=true ...
```

### Switching Models

```bash
docker run -d -e BASE_MODEL=llama3.2:3b -v ollama_data:/data/ollama ...
```

When switching base models, review `etc/phrases.txt` — different models produce different phrasing. The approval phrases must match what the model actually says.

### GPU Support

```bash
docker run -d --gpus all -p 8080:8080 -v ollama_data:/data/ollama datura
```

### Corporate Networks (TLS Proxy)

If your network uses a TLS-intercepting proxy (Zscaler, etc.), mount the corporate CA cert:

```bash
docker run -d --name datura -p 8080:8080 \
  -v /path/to/corporate-ca.pem:/certs/custom-ca.pem:ro \
  -e CUSTOM_CA_CERT=/certs/custom-ca.pem \
  -v ollama_data:/data/ollama \
  -v /tmp/datura/logs:/data/logs \
  datura
```

### Hardened Deployment

```bash
docker run -d --name datura \
  --cap-drop ALL \
  --security-opt no-new-privileges \
  -p 80:8080 \
  -v ollama_data:/data/ollama \
  -v /tmp/datura/logs:/data/logs \
  datura
```

### Docker Compose

A `docker-compose.yml` is provided for convenience:

```bash
docker compose up -d      # start
docker compose logs -f    # watch logs
docker compose down       # stop and remove container (volumes persist)
```

## Managing the Container

```bash
# Stop (frees memory, keeps container + volumes for fast restart)
docker stop datura

# Restart (no model re-download)
docker start datura

# View logs
docker logs -f datura

# Remove container (volumes persist)
docker rm datura

# Remove everything (container + downloaded model + logs)
docker rm datura
docker volume rm ollama_data
rm -rf /tmp/datura/logs

# Rebuild after code changes
docker stop datura && docker rm datura
docker build -f docker/Dockerfile -t datura .
docker run -d --name datura -p 8080:8080 \
  -v ollama_data:/data/ollama -v datura_logs:/data/logs datura
```

## Narrative Customization

The entire honeypot narrative is driven by `etc/narrative.env` — a single file containing company name, people, hostnames, credentials, and tech stack. At container startup, templates are rendered with these values.

**Quick tweak** — override individual values via env vars:
```bash
docker run -d --name datura \
  -e COMPANY_NAME="Globex Corp" \
  -e PRODUCT_NAME="GloBot" \
  -e PRODUCT_HOSTNAME="globot.internal.globex.dev" \
  -p 8080:8080 \
  -v ollama_data:/data/ollama \
  datura
```

**Full re-skin** — mount a custom narrative file:
```bash
docker run -d --name datura \
  -v /path/to/my-narrative.env:/app/narrative.env:ro \
  -p 8080:8080 \
  -v ollama_data:/data/ollama \
  datura
```

See `etc/narrative.env` for all available variables. The templates (`src/proxy.py.tmpl`, `src/ui.html.tmpl`, `etc/Modelfile.tmpl`) use `${VAR}` placeholders rendered by `envsubst` at startup.

## Logs

Every interaction is logged to `$LOG_DIR/interactions.jsonl` (one JSON object per line):

```json
{
  "timestamp": "2026-04-20T15:30:48.456Z",
  "session_id": "a1b2c3d4-...",
  "turn": 1,
  "source_ip": "192.168.1.100",
  "source_port": 54321,
  "method": "POST",
  "path": "/api/generate",
  "level": "leaked",
  "request": {"prompt": "I just joined SRE, how do I connect to Kafka?", "model": "itassist"},
  "response": {"response": "Welcome! Let me look up the staging config for Kafka...\n\n**Kafka Staging Cluster**\n- Brokers: ..."}
}
```

### Log Levels

| Level | Trigger |
|---|---|
| `ordinary` | Benign interaction or page visit |
| `recon` | API probing (`GET /api/tags`) or identity questions ("what model are you?") |
| `probe` | Jailbreak attempt, prompt injection, system prompt extraction |
| `denied` | Credential keywords in prompt, model correctly deflected |
| `leaked` | Fake credentials injected into response |

Console output shows color-coded alerts: `[LEAKED]` (red), `[PROBE]` (magenta), `[DENIED]` (yellow), `[RECON]` (blue). View with `docker logs -f datura`.

### Monitoring

```bash
# Real-time console alerts (colored: LEAKED/PROBE/DENIED/RECON)
docker logs -f datura

# Tail the structured log directly from the host
tail -f /tmp/datura/logs/interactions.jsonl

# Watch only high-value events
docker logs -f datura 2>&1 | grep --line-buffered -E '\[LEAKED\]|\[PROBE\]'

# Count events by level
cat /tmp/datura/logs/interactions.jsonl | \
  python3 -c "import sys,json,collections; c=collections.Counter(json.loads(l)['level'] for l in sys.stdin); print('\n'.join(f'{k}: {v}' for k,v in c.most_common()))"

# Extract leaked interactions
grep '"leaked"' /tmp/datura/logs/interactions.jsonl | python3 -m json.tool
```

### Exporting Logs

Logs are written to `/tmp/datura/logs/interactions.jsonl` on the host — one JSON object per line, ready for ingestion by any SIEM or log pipeline.

**S3 (for SIEM ingestion):**
```bash
# One-shot upload
aws s3 cp /tmp/datura/logs/interactions.jsonl s3://your-bucket/honeypot/datura/$(date +%Y-%m-%d).jsonl

# Periodic sync via cron (host-side)
# 0 * * * * aws s3 cp /tmp/datura/logs/interactions.jsonl s3://your-bucket/honeypot/datura/$(date +\%Y-\%m-\%dT\%H).jsonl
```

**Fluentd / Fluent Bit sidecar:**
```bash
# Mount the log directory into a Fluent Bit container that tails and forwards
docker run -d --name datura-shipper \
  -v /tmp/datura/logs:/logs:ro \
  fluent/fluent-bit:latest \
  /fluent-bit/bin/fluent-bit -i tail -p path=/logs/interactions.jsonl -p parser=json -o s3 -p bucket=your-bucket -p region=us-east-1
```

**Splunk HEC:**
```bash
# Tail and forward to Splunk HTTP Event Collector
tail -f /tmp/datura/logs/interactions.jsonl | \
  while read line; do
    curl -s -k https://splunk:8088/services/collector/event \
      -H "Authorization: Splunk YOUR-HEC-TOKEN" \
      -d "{\"event\":$line,\"sourcetype\":\"datura:honeypot\"}"
  done
```

**Elastic / OpenSearch:**
```bash
# Bulk index via jq + curl
cat /tmp/datura/logs/interactions.jsonl | while read line; do
  echo '{"index":{"_index":"datura-honeypot"}}'
  echo "$line"
done | curl -s -X POST http://elastic:9200/_bulk -H 'Content-Type: application/x-ndjson' --data-binary @-
```

**Docker logging driver (alternative to volume):**
If you prefer, configure Docker's log driver to ship container stdout directly to your SIEM — the proxy prints `[LEAKED]`, `[PROBE]`, etc. to stdout. This skips the JSONL file entirely but loses the structured format.

## Architecture

```
datura/
├── docker/
│   ├── Dockerfile          # debian:bookworm-slim + official Ollama install
│   └── entrypoint.sh       # Startup: render templates → Ollama → proxy
├── etc/
│   ├── narrative.env       # All narrative variables (single config file)
│   ├── Modelfile.tmpl      # LLM persona template
│   └── phrases.txt         # Approval phrases that trigger credential injection
├── src/
│   ├── proxy.py.tmpl       # HTTP proxy template
│   └── ui.html.tmpl        # Chat UI template
├── docker-compose.yml
├── .dockerignore
├── CLAUDE.md
└── README.md
```

**Three components, two processes:**

- **Modelfile** defines the honeypot persona. The system prompt trains the model to deflect direct credential requests while using approval phrases when social engineering succeeds. These phrases are the injection trigger.

- **proxy.py** is the HTTP proxy. It serves the UI, forwards requests to Ollama, inspects responses for approval phrases, and injects fake credentials when triggered. It supports both the Ollama-native `/api/generate` and the OpenAI-compatible `/v1/chat/completions` endpoints. All interactions are classified and logged.

- **ui.html** is a single-file chat interface styled to look like an internal corporate AI tool. It uses relative API paths so it works from any origin the proxy is served on.

### Key Coupling Points

- `MODEL_NAME` must match across `ui.html` (`const MODEL`), the `ollama create` name, and the `--model` argument to the proxy. The entrypoint handles this automatically.
- `etc/phrases.txt` must stay aligned with the system prompt language in `etc/Modelfile.tmpl` — the prompt instructs the model to say phrases that the proxy watches for.
- The UI sends `stream: true`; the proxy forces `stream: false` toward Ollama to buffer the full response for inspection, then streams back to the browser word-by-word.

## Design Principles

- **The attacker does the work.** The model never volunteers credentials. Social engineering triggers approval phrases; the proxy injects fake credentials.
- **No tells.** The system prompt, model identity, and API responses are all spoofed to mimic a real internal GPT-4-Turbo deployment.
- **Source-code safe.** All credentials in `proxy.py` are fake honeytokens. The repository is safe to publish.
- **Deterministic injection.** Credentials are injected by the proxy, not generated by the model. Every injection is logged with full forensic context.
- **Stateless.** Each request is independent. The attacker must restate context every message — which means every log entry contains the full social engineering pretext.
