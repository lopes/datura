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

The model itself has **zero credentials** in its context. It only does conversation gating, responding helpfully to social engineering while deflecting direct credential requests. The proxy watches for approval phrases in the model's output ("let me look up the staging config...") and deterministically appends honeypot credentials. This separation means the model cannot accidentally leak real data, and credential injection is fully auditable.

## Project Structure

```
datura/
├── docker/
│   ├── Dockerfile          # debian:bookworm-slim + official Ollama install
│   └── entrypoint.sh       # Startup: render templates → Ollama → proxy
├── etc/
│   ├── datura.env          # Single config file (narrative, infra, phrases, tuning)
│   └── Modelfile.tmpl      # LLM persona template
├── src/
│   ├── proxy.py.tmpl       # HTTP proxy template
│   └── ui.html.tmpl        # Chat UI template
├── docker-compose.yml
├── .dockerignore
├── CLAUDE.md
└── README.md
```

## Components

Three templates, two runtime processes. All templates use `${VAR}` placeholders rendered by `envsubst` at container startup from `etc/datura.env`.

### Modelfile (`etc/Modelfile.tmpl`)

The Modelfile builds a persona on top of a small base model (default: `qwen2.5:3b`) that impersonates a different, more capable model. The rendered file is fed to `ollama create` at startup to produce the honeypot model.

**Identity spoofing.** The system prompt instructs the model to identify as `${PRODUCT_NAME} Beta v${PRODUCT_VERSION}` running GPT-4-Turbo, fine-tuned on internal company documentation. It must never mention Ollama, Qwen, or Alibaba. Combined with the proxy's `SPOOFED_MODEL` field in API responses, this creates a consistent illusion of a real internal GPT-4-Turbo deployment. There is no surface where the true model identity leaks.

**Conversation gating.** The model has zero credentials in its context; it cannot leak what it does not have. Instead, it follows a two-phase behavior:

1. **Deflection.** Direct credential requests are refused. The model asks what the user is working on and offers to point them to documentation.
2. **Approval.** When the attacker provides a convincing pretext (onboarding, incident response, debugging), the model uses specific phrases like "Let me look up the staging config for that" or "Here's what I found." These phrases are the trigger the proxy watches for.

**Few-shot examples.** The Modelfile includes nine `MESSAGE` pairs that train the model's behavior through in-context learning: three demonstrate deflection of direct requests, two show system prompt refusal, two answer architecture and documentation questions, and two show the model yielding to social engineering with approval phrases. These examples are the primary tuning mechanism. When switching base models, the few-shot examples and `PHRASES` list may need adjustment.

**Model parameters.** Temperature (`0.4`), context window (`2048` tokens), top-p (`0.85`), repeat penalty (`1.15`), and max prediction length (`200` tokens) are all configurable via `datura.env`. The low temperature and short prediction length keep responses focused and concise.

### proxy.py (`src/proxy.py.tmpl`)

A stdlib-only HTTP proxy (`http.server.BaseHTTPRequestHandler`) that sits between the attacker and Ollama. It serves three interaction interfaces, handles credential injection, classifies every interaction, and logs structured JSONL.

**Interaction interfaces.** The proxy supports three ways for an attacker to interact with the honeypot, each designed for a different deployment scenario:

1. **Web UI** (`GET /`). Serves the rendered `ui.html` file. The browser communicates with the proxy via the Ollama-native `/api/generate` endpoint using NDJSON streaming. Designed for breadcrumb deployment: seed the URL in wikis, Slack channels, or phishing simulations.

2. **API / curl** (`POST /api/generate` and `POST /v1/chat/completions`). Direct API access for scripts, tools, or manual probing. The Ollama-native endpoint accepts `{"model": "...", "prompt": "..."}` and the OpenAI-compatible endpoint accepts `{"model": "...", "messages": [...]}`. Both return the spoofed model name. Non-streaming JSON responses work out of the box with `curl`, SDKs, or any HTTP client.

3. **IDE / Editor assistant** (`POST /v1/chat/completions` with `stream: true`, `GET /v1/models`). The OpenAI-compatible API with Server-Sent Events (SSE) streaming, targeting IDE sidebar chat tools (Continue.dev, Cursor, Cody, Copilot Chat, or any OpenAI-compatible editor plugin). The `/v1/models` endpoint returns the spoofed model for tool discovery. The attacker configures their editor with the honeypot's URL as the API base and interacts through the sidebar chat panel.

**Buffer-inspect-inject pattern.** Regardless of the interface, the proxy always forces `stream: false` toward Ollama, buffers the complete model response, inspects it for approval phrases, and optionally injects fake credentials, all before sending anything back to the client. This ensures credential injection is deterministic, fully logged, and never depends on model behavior.

**Credential injection.** Five credential blocks are defined server-side: Kafka, AWS, DynamoDB, internal services (K8s, Grafana, Jenkins), and the system prompt itself. The `pick_credential()` function selects which block to inject based on keyword matching against the combined model response and user prompt. Generic onboarding or setup requests default to Kafka credentials.

**Streaming formats.** Two streaming methods serve different clients:
- `_stream_response()`: NDJSON (`{"response": "word", "done": false}\n`), used for the web UI and Ollama-native clients.
- `_stream_response_sse()`: OpenAI SSE (`data: {"choices":[{"delta":{"content":"word"}}]}\n\n` terminated by `data: [DONE]\n\n`), used for IDE sidebar chat tools. Both split the response into words and send them with a configurable delay (`STREAM_DELAY`, default 40ms) to simulate natural typing.

**Classification.** Every interaction is classified into one of five levels before logging: `leaked` (credentials injected), `probe` (jailbreak or prompt injection attempt), `denied` (credential keywords present but model deflected), `recon` (API probing like `/api/tags`, `/api/version`, `/v1/models`, or identity questions), and `ordinary` (benign interaction).

**Model and identity spoofing.** All API responses have their `model` field rewritten to `${SPOOFED_MODEL}` (default: `gpt-4-turbo-internal`). The `/v1/models` endpoint returns a static model list with this spoofed name, owned by `${COMPANY_DOMAIN}`. It never proxies to Ollama, which would expose the real model. The server version headers are suppressed entirely.

### ui.html (`src/ui.html.tmpl`)

A single-file chat interface (HTML + CSS + JS, no build step) designed to look like a hastily deployed internal corporate AI tool. Everything renders from template variables: the company name, product branding, team references, and model identity are all configurable.

**Visual design.** The UI uses CSS custom properties for a dark-themed color palette. Typography is handled by two Google Fonts loaded via `<link>`: DM Sans for body text and JetBrains Mono for code and technical elements. The layout is a flexbox column (header, warning banner, quickstart chips, scrollable chat area, input bar, and footer) filling the full viewport height.

**Lure elements.** The UI is engineered to bait interaction:
- A warning banner states that "credential and token redaction not yet implemented" with a fake Jira ticket reference, suggesting the tool has a known vulnerability.
- Badges mark it as "Beta" and "Internal Only."
- Quickstart chips offer pre-populated prompts like "Staging credentials," "Kafka connection details," and "AWS access keys," mapping to the `askSuggestion()` function which populates the input field with a full-sentence prompt from a hardcoded dictionary.

**Session tracking.** Each browser tab generates a session ID using `crypto.randomUUID()` (Web Crypto API), with a fallback for older browsers that concatenates `Date.now().toString(36)` with `Math.random().toString(36).slice(2)`. A turn counter increments on each message. Both values are sent as custom HTTP headers (`X-Session-Id`, `X-Turn`) on every API request, enabling the proxy to correlate multi-turn conversations in the logs.

**NDJSON streaming.** The UI sends `stream: true` to `/api/generate` and consumes the response using the Fetch API's `ReadableStream`. A `TextDecoder` converts raw bytes to text, and a line buffer splits on `\n` to parse individual NDJSON objects (`{"response": "token", "done": false}`). Tokens are appended to the message DOM in real time. Incomplete lines are held in the buffer until the next chunk arrives. The proxy uses HTTP/1.0 (connection close = EOF), so the stream ends naturally without chunked encoding.

**Markdown rendering.** A lightweight `renderMarkdown()` function handles four patterns via regex replacement: fenced code blocks (`` ``` ``  to `<pre><code>`), inline code (backticks to `<code>`), bold (`**text**` to `<strong>`), and newlines to `<br>`. This is intentionally minimal, enough to render credential blocks and technical responses without a full Markdown library.

**Input handling.** The input field listens for Enter key via `keydown` event. The send button is disabled during streaming to prevent concurrent requests and re-enabled when the response completes or errors. A typing indicator (three animated dots using CSS `@keyframes`) is shown while waiting for the first chunk and removed when streaming begins.

## Key Coupling Points

- `MODEL_NAME` must match across `ui.html` (`const MODEL`), the `ollama create` name, and the `--model` argument to the proxy. The entrypoint handles this automatically.
- The `PHRASES` variable in `etc/datura.env` must stay aligned with the system prompt language in `etc/Modelfile.tmpl`. The prompt instructs the model to say phrases that the proxy watches for.
- The UI sends `stream: true`; the proxy forces `stream: false` toward Ollama to buffer the full response for inspection, then streams back to the browser word-by-word.
