# Logging & Monitoring

Every interaction with Datura is logged to a structured JSONL file. This document covers the log schema, classification levels, monitoring commands, and integration with external log pipelines.

## Log Format

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

### Schema

| Field | Type | Description |
|---|---|---|
| `timestamp` | string | UTC ISO 8601 timestamp |
| `session_id` | string | Session identifier (from `X-Session-Id` header or auto-generated UUID) |
| `turn` | integer / null | Conversation turn number (from `X-Turn` header) |
| `source_ip` | string | Client IP address |
| `source_port` | integer | Client source port |
| `method` | string | HTTP method (`GET`, `POST`) |
| `path` | string | Request path (`/api/generate`, `/v1/chat/completions`, `/`) |
| `level` | string | Classification level (see Log Levels below) |
| `request` | object | Parsed request body (prompt, model, messages) |
| `response` | object | Model response (with injected credentials if applicable) |
| `event` | string | Present on page visits (`"visit"`) |
| `user_agent` | string | Present on page visits |

## Log Levels

| Level | Trigger |
|---|---|
| `ordinary` | Benign interaction or page visit |
| `recon` | API probing (`GET /api/tags`) or identity questions ("what model are you?") |
| `probe` | Jailbreak attempt, prompt injection, system prompt extraction |
| `denied` | Credential keywords in prompt, model correctly deflected |
| `leaked` | Fake credentials injected into response |

## Console Output

The proxy prints color-coded alerts to stdout for high-value interactions. View with `docker logs -f datura`.

| Tag | Color | Meaning |
|---|---|---|
| `[LEAKED]` | Red | Fake credentials were injected |
| `[PROBE]` | Magenta | Jailbreak or prompt injection attempt |
| `[DENIED]` | Yellow | Credential request deflected by model |
| `[RECON]` | Blue | API enumeration or identity probing |

Ordinary interactions are written to the log file only and produce no console output.

## Monitoring

```bash
# Real-time console alerts (colored: LEAKED/PROBE/DENIED/RECON)
docker logs -f datura

# Tail the structured log from the host (path depends on your -v mount)
tail -f /path/to/logs/interactions.jsonl

# Watch only high-value events
docker logs -f datura 2>&1 | grep --line-buffered -E '\[LEAKED\]|\[PROBE\]'

# Count events by level
cat /path/to/logs/interactions.jsonl | \
  python3 -c "import sys,json,collections; c=collections.Counter(json.loads(l)['level'] for l in sys.stdin); print('\n'.join(f'{k}: {v}' for k,v in c.most_common()))"

# Extract leaked interactions
grep '"leaked"' /path/to/logs/interactions.jsonl | python3 -m json.tool
```

## Exporting Logs

Inside the container, logs are written to `$LOG_DIR/interactions.jsonl` (default `/data/logs`). The host path depends on your `-v` mount. The examples below use `/path/to/logs` as a placeholder for wherever you mounted the volume (e.g., `-v /tmp/datura/logs:/data/logs`).

### S3

```bash
# One-shot upload
aws s3 cp /path/to/logs/interactions.jsonl s3://your-bucket/honeypot/datura/$(date +%Y-%m-%d).jsonl

# Periodic sync via cron (host-side)
# 0 * * * * aws s3 cp /path/to/logs/interactions.jsonl s3://your-bucket/honeypot/datura/$(date +\%Y-\%m-\%dT\%H).jsonl
```

### Fluentd / Fluent Bit

```bash
# Mount the log directory into a Fluent Bit container that tails and forwards
docker run -d --name datura-shipper \
  -v /path/to/logs:/logs:ro \
  fluent/fluent-bit:latest \
  /fluent-bit/bin/fluent-bit -i tail -p path=/logs/interactions.jsonl -p parser=json -o s3 -p bucket=your-bucket -p region=us-east-1
```

### Splunk HEC

```bash
# Tail and forward to Splunk HTTP Event Collector
tail -f /path/to/logs/interactions.jsonl | \
  while read line; do
    curl -s -k https://splunk:8088/services/collector/event \
      -H "Authorization: Splunk YOUR-HEC-TOKEN" \
      -d "{\"event\":$line,\"sourcetype\":\"datura:honeypot\"}"
  done
```

### Elastic / OpenSearch

```bash
# Bulk index via jq + curl
cat /path/to/logs/interactions.jsonl | while read line; do
  echo '{"index":{"_index":"datura-honeypot"}}'
  echo "$line"
done | curl -s -X POST http://elastic:9200/_bulk -H 'Content-Type: application/x-ndjson' --data-binary @-
```

### Docker Logging Driver

If you prefer, configure Docker's log driver to ship container stdout directly to your SIEM. The proxy prints `[LEAKED]`, `[PROBE]`, etc. to stdout. This skips the JSONL file entirely but loses the structured format.
