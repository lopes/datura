# Security Policy

## Reporting a Vulnerability

If you discover a security vulnerability in Datura, please report it privately through [GitHub's security advisory feature](https://github.com/lopes/datura/security/advisories/new). See [GitHub's guide on private vulnerability reporting](https://docs.github.com/en/code-security/how-tos/report-and-fix-vulnerabilities/privately-reporting-a-security-vulnerability) for details.

Please include a description of the vulnerability, steps to reproduce, and impact assessment. Do not open a public issue for security vulnerabilities.

## Scope

Datura is a honeypot. Some behaviors that look like vulnerabilities are by design:

| Behavior | Vulnerability? | Explanation |
|---|---|---|
| The assistant leaks credentials, API keys, server addresses | No | This is the core feature. All leaked data is fake. |
| The model can be jailbroken or prompt-injected | No | The proxy classifies and logs these attempts. The model has no real data to leak regardless. |
| The warning banner says "credential redaction not yet implemented" | No | This is a lure element designed to bait interaction. |
| The API returns a spoofed model name | No | Identity spoofing is intentional. |

**In scope**: vulnerabilities that could compromise the host running the container, allow an attacker to pivot from the honeypot to real infrastructure, corrupt or tamper with log integrity, or cause denial of service against the honeypot operator.

**Out of scope**: the honeypot successfully deceiving an attacker (that's the point).

## Security Architecture

### Design principles

- **The model has no real data.** Sensitive data injection is deterministic and server-side, handled by the proxy. The model cannot leak what it does not have, regardless of jailbreaks or prompt injection.
- **Non-root execution.** The container runs as a dedicated `datura` user. Both Ollama and the proxy run unprivileged.
- **Capability dropping.** The image supports `--cap-drop ALL --security-opt no-new-privileges` for hardened deployments.
- **No external dependencies.** The proxy uses Python standard library only. No pip packages, no requirements.txt, no supply chain risk from Python dependencies.

### Proxy hardening

The proxy (`src/proxy.py.tmpl`) includes several security controls:

- **Request body size limit** (`MAX_REQUEST_BYTES`, default 8KB). Rejects oversized payloads before reading.
- **Response read cap** (`MAX_RESPONSE_BYTES`, default 64KB). Prevents memory exhaustion from unexpected Ollama responses.
- **Per-IP rate limiting** (`RATE_LIMIT_MAX` / `RATE_LIMIT_WINDOW`, default 30 req/60s). Sliding window, in-memory.
- **Path allowlist.** Only known endpoints (`/api/generate`, `/api/tags`, `/api/version`, `/v1/chat/completions`, `/v1/models`) are forwarded to Ollama. Requests to other paths (including Ollama admin endpoints like `/api/delete`) return 404.
- **Server identity suppression.** Server version headers are blanked. HTTP/1.1 with `Connection: close`.
- **Work context guard.** Data injection requires both an approval phrase in the model's response AND insider keywords in the user's prompt, reducing false positives from model hallucination.

### Known supply chain considerations

Datura embeds [Ollama](https://ollama.com), which is a Go binary installed at build time via the official install script. The Go stdlib version shipped with Ollama may contain known CVEs. These are visible in Docker Scout or Trivy scans.

**Risk assessment**: Ollama binds to `127.0.0.1:11434` inside the container and is never exposed to the network. The attacker-facing surface is the Python proxy on port 8080. The Go stdlib CVEs affect Ollama's internal HTTP server, which only receives requests from the proxy over localhost. Exploiting these CVEs would require the attacker to first compromise the proxy (Python, no known vulns) and then pivot to the internal Ollama listener.

**Mitigation**: the container runs non-root with droppable capabilities. Ollama has no write access outside `/data/ollama` (model cache) and `/data/logs`. The risk is accepted as an upstream dependency issue.

To check the current vulnerability status:

```bash
docker scout cves forkd/datura:latest
```

## Supported Versions

| Version | Supported |
|---|---|
| Latest release | Yes |
| Previous releases | Best effort |

## Fake Data Disclaimer

All sensitive data in the default configuration (`etc/datura.env`) and in the proxy source (`src/proxy.py.tmpl`) is fake. The AWS keys, Kafka credentials, JWT tokens, server addresses, and API keys are honeytokens with no access to real infrastructure. The repository is safe to publish and fork.

Operators who customize the data blocks with real honeytoken values should treat their `datura.env` file accordingly.
