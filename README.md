# Datura

An LLM honeypot for detection engineering. It deploys a convincing but fake internal AI assistant that appears to leak sensitive data — credentials, API keys, connection strings — when socially engineered. Every interaction is logged, giving defenders a high-fidelity signal of attacker intent and technique.

Named after [*Datura stramonium*](https://en.wikipedia.org/wiki/Datura_stramonium) — a plant that appears ordinary but is highly toxic. The honeypot looks like a misconfigured internal tool; what the attacker extracts is the poison.

## Table of Contents

- [How It Works](#how-it-works)
- [Quick Start](#quick-start)
- [Use Cases](#use-cases)
- [Configuration](#configuration)
- [Managing the Container](#managing-the-container)
- [Documentation](#documentation)
- [Design Principles](#design-principles)
- [License](#license)

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

## Documentation

- **[Architecture](docs/architecture.md)** — project structure, component breakdown, and how the proxy, model, and UI fit together.
- **[Logging & Monitoring](docs/logging.md)** — log format, classification levels, monitoring commands, and SIEM integration (S3, Splunk, Elastic, Fluentd).
- **[Narrative Customization](docs/narrative.md)** — re-skinning the honeypot identity, credentials, Web UI, and building a believable narrative for adversary engagement.

## Design Principles

Datura implements several activities from the [MITRE Engage](https://engage.mitre.org/) framework for adversary engagement. It acts as a **Lure** by seeding breadcrumbs that draw adversaries toward the honeypot. The assistant itself is a **Decoy Artifact** — a convincing but fake internal tool whose responses contain honeytoken credentials. Every interaction feeds the **Monitoring** activity, producing structured logs that capture attacker intent, technique, and social engineering pretexts. The following principles guide these engagement activities.

- **The attacker does the work.** The model never volunteers credentials. Social engineering triggers approval phrases; the proxy injects fake credentials.
- **No tells.** The system prompt, model identity, and API responses are all spoofed to mimic a real internal GPT-4-Turbo deployment.
- **Source-code safe.** All credentials in `proxy.py` are fake honeytokens. The repository is safe to publish.
- **Deterministic injection.** Credentials are injected by the proxy, not generated by the model. Every injection is logged with full forensic context.
- **Stateless.** Each request is independent. The attacker must restate context every message — which means every log entry contains the full social engineering pretext.

## License

MIT. See [LICENSE](LICENSE).
