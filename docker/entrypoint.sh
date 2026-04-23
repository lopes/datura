#!/usr/bin/env bash
set -e

# ── Fix volume permissions (volumes may be root-owned from prior runs) ──
chown -R datura:datura /data/logs /data/ollama /etc/stunnel 2>/dev/null || true

# ── Append custom CA cert to system bundle (for corporate TLS proxies) ──
if [ -n "$CUSTOM_CA_CERT" ] && [ -f "$CUSTOM_CA_CERT" ]; then
    cat "$CUSTOM_CA_CERT" >> /etc/ssl/certs/ca-certificates.crt
    echo "[*] Custom CA cert appended from $CUSTOM_CA_CERT"
fi

# ── Load config (docker -e vars take precedence over file defaults) ──
_saved_env=$(export -p)
set -a
source /app/datura.env
set +a
eval "$_saved_env"

# ── TLS_HOSTNAME defaults to PRODUCT_HOSTNAME from narrative ──
TLS_HOSTNAME="${TLS_HOSTNAME:-$PRODUCT_HOSTNAME}"

# ── Generate phrases.txt from config ──
if [ -n "$PHRASES_FILE" ] && [ -f "$PHRASES_FILE" ]; then
    cp "$PHRASES_FILE" /app/phrases.txt
    echo "[*] Phrases loaded from external file: $PHRASES_FILE"
else
    echo "$PHRASES" | tr '|' '\n' | sed '/^\s*$/d' > /app/phrases.txt
    echo "[*] Phrases generated from PHRASES variable ($(wc -l < /app/phrases.txt) phrases)"
fi

# ── Render templates ──
# Explicit variable lists prevent envsubst from eating bare $ patterns
# (e.g., regex backreferences $1, $2 in JavaScript or Python).
_ui_tmpl="${UI_FILE%.html}.html.tmpl"
_ui_vars='${PRODUCT_NAME} ${LOGO_TEXT} ${TEAM_NAME} ${PRODUCT_VERSION} ${PRODUCT_HOSTNAME} ${SPOOFED_MODEL} ${TEAM_PREFIX} ${TEAM_CHANNEL} ${MODEL_NAME}'
_proxy_vars='${PRODUCT_NAME} ${MODEL_NAME} ${MAX_REQUEST_BYTES} ${MAX_RESPONSE_BYTES} ${RATE_LIMIT_WINDOW} ${RATE_LIMIT_MAX} ${UI_FILE} ${COMPOSITE_BLOCKS} ${DEFAULT_COMPOSITE} ${DEFAULT_COMPOSITE_KEYWORDS} ${EXTRA_WORK_CONTEXT} ${SENSITIVE_KEYWORDS} ${PROBE_PATTERNS} ${RECON_PATTERNS} ${SPOOFED_MODEL} ${COMPANY_DOMAIN} ${STREAM_DELAY} ${OLLAMA_TIMEOUT}'
_model_vars='${BASE_MODEL} ${PRODUCT_NAME} ${PRODUCT_VERSION} ${COMPANY_NAME} ${TEAM_NAME} ${SPOOFED_MODEL_LABEL} ${PRODUCT_HOSTNAME} ${TEAM_CHANNEL} ${CLI_TOOL} ${TECH_STACK} ${LEAD_NAME} ${LEAD_HANDLE} ${LEAD_ROLE} ${SECURITY_NAME} ${SECURITY_HANDLE} ${FORBIDDEN_MODEL_NAMES} ${MODEL_TEMPERATURE} ${MODEL_NUM_CTX} ${MODEL_TOP_P} ${MODEL_REPEAT_PENALTY} ${MODEL_NUM_PREDICT}'
envsubst "$_proxy_vars" < /app/proxy.py.tmpl       > /app/proxy.py
envsubst "$_ui_vars"    < "/app/${_ui_tmpl}"        > "/app/${UI_FILE}"
envsubst "$_model_vars" < /app/Modelfile.tmpl       > /app/Modelfile

echo "[*] Narrative: ${PRODUCT_NAME} @ ${COMPANY_NAME} (${PRODUCT_HOSTNAME})"
echo "[*] Composite blocks: $(echo "$COMPOSITE_BLOCKS" | tr '|' ', ') (default: $DEFAULT_COMPOSITE)"

# ── Start Ollama daemon (as datura) ──
echo "[*] Starting Ollama..."
su -s /bin/bash datura -c \
    "OLLAMA_HOST=$OLLAMA_HOST OLLAMA_MODELS=/data/ollama OLLAMA_ORIGINS='*' ollama serve >> $LOG_DIR/ollama.log 2>&1" &
OLLAMA_PID=$!

# Wait for Ollama to be ready
for i in $(seq 1 30); do
    if curl -sf "http://${OLLAMA_HOST}/api/version" > /dev/null 2>&1; then
        echo "[*] Ollama ready"
        break
    fi
    if [ "$i" -eq 30 ]; then
        echo "[!] Ollama failed to start within 30s"
        exit 1
    fi
    sleep 1
done

# ── Pull base model (idempotent — skips if cached in volume) ──
echo "[*] Pulling base model: $BASE_MODEL"
ollama pull "$BASE_MODEL"

# ── Create honeypot model ──
echo "[*] Creating honeypot model: $MODEL_NAME"
ollama create "$MODEL_NAME" -f /app/Modelfile

# ── Optional TLS via stunnel ──
if [ "$GENERATE_SELF_SIGNED" = "true" ] && [ -z "$TLS_CERT" ]; then
    TLS_CERT="/etc/stunnel/selfsigned.pem"
    TLS_KEY="/etc/stunnel/selfsigned.key"
    openssl req -x509 -newkey rsa:2048 \
        -keyout "$TLS_KEY" -out "$TLS_CERT" \
        -days 365 -nodes \
        -subj "/CN=${TLS_HOSTNAME}" \
        2>/dev/null
    echo "[*] Generated self-signed cert for $TLS_HOSTNAME"
fi

if [ -n "$TLS_CERT" ] && [ -n "$TLS_KEY" ]; then
    cat > /etc/stunnel/stunnel.conf <<STCONF
pid = /tmp/stunnel.pid
[https]
accept = 0.0.0.0:${TLS_PORT}
connect = 127.0.0.1:${PROXY_PORT}
cert = ${TLS_CERT}
key = ${TLS_KEY}
STCONF
    stunnel /etc/stunnel/stunnel.conf
    echo "[*] TLS enabled on port $TLS_PORT -> proxy port $PROXY_PORT"
fi

# ── Clean shutdown ──
cleanup() {
    kill "$OLLAMA_PID" 2>/dev/null
    wait "$OLLAMA_PID" 2>/dev/null
}
trap cleanup EXIT TERM INT

# ── Start proxy as datura (exec replaces shell — receives Docker signals) ──
echo "[*] Starting proxy on port $PROXY_PORT"
exec su -s /bin/bash datura -c "exec python3 /app/proxy.py \
    --model   '${MODEL_NAME}' \
    --log-dir '${LOG_DIR}' \
    --port    '${PROXY_PORT}' \
    --ollama  'http://${OLLAMA_HOST}' \
    --phrases /app/phrases.txt"
