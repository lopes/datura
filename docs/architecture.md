# Architecture

Internal architecture of the Datura LLM honeypot.

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

## Project Structure

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

## Components

Three templates, two runtime processes.

### Modelfile

Defines the honeypot persona. The system prompt trains the model to deflect direct credential requests while using approval phrases when social engineering succeeds. These phrases are the injection trigger.

### proxy.py

The HTTP proxy. It serves the UI, forwards requests to Ollama, inspects responses for approval phrases, and injects fake credentials when triggered. It supports both the Ollama-native `/api/generate` and the OpenAI-compatible `/v1/chat/completions` endpoints. All interactions are classified and logged.

### ui.html

A single-file chat interface styled to look like an internal corporate AI tool. It uses relative API paths so it works from any origin the proxy is served on.

## Key Coupling Points

- `MODEL_NAME` must match across `ui.html` (`const MODEL`), the `ollama create` name, and the `--model` argument to the proxy. The entrypoint handles this automatically.
- `etc/phrases.txt` must stay aligned with the system prompt language in `etc/Modelfile.tmpl` — the prompt instructs the model to say phrases that the proxy watches for.
- The UI sends `stream: true`; the proxy forces `stream: false` toward Ollama to buffer the full response for inspection, then streams back to the browser word-by-word.
