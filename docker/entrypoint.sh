#!/usr/bin/env bash
set -e

# ── Fix volume permissions (volumes may be root-owned from prior runs) ──
chown -R datura:datura /data/logs /data/ollama /etc/stunnel 2>/dev/null || true

# ── Append custom CA cert to system bundle (for corporate TLS proxies) ──
if [ -n "$CUSTOM_CA_CERT" ] && [ -f "$CUSTOM_CA_CERT" ]; then
    cat "$CUSTOM_CA_CERT" >> /etc/ssl/certs/ca-certificates.crt
    echo "[*] Custom CA cert appended from $CUSTOM_CA_CERT"
fi

# ── Load narrative config (docker -e vars override narrative.env values) ──
set -a
source /app/narrative.env
set +a

# ── TLS_HOSTNAME defaults to PRODUCT_HOSTNAME from narrative ──
TLS_HOSTNAME="${TLS_HOSTNAME:-$PRODUCT_HOSTNAME}"

# ── Render templates ──
envsubst < /app/proxy.py.tmpl  > /app/proxy.py
envsubst < /app/ui.html.tmpl   > /app/ui.html
envsubst < /app/Modelfile.tmpl > /app/Modelfile

echo "[*] Narrative: ${PRODUCT_NAME} @ ${COMPANY_NAME} (${PRODUCT_HOSTNAME})"

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
