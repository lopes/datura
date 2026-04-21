# Minimal hardened runtime
FROM debian:bookworm-slim

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
       python3 stunnel4 openssl curl ca-certificates zstd gettext-base \
    && curl -fsSL https://ollama.com/install.sh | sh \
    && rm -rf /var/lib/apt/lists/*

# Non-root user
RUN groupadd -r datura && useradd -r -g datura -d /app -s /usr/sbin/nologin datura \
    && mkdir -p /app /data/logs /data/ollama /etc/stunnel \
    && chown -R datura:datura /app /data/logs /data/ollama /etc/stunnel

WORKDIR /app
COPY --chown=datura:datura src/proxy.py.tmpl src/ui.html.tmpl ./
COPY --chown=datura:datura etc/Modelfile.tmpl etc/datura.env ./
COPY --chown=datura:datura docker/entrypoint.sh ./
RUN chmod +x entrypoint.sh

EXPOSE 8080 8443
VOLUME ["/data/logs", "/data/ollama"]

HEALTHCHECK --interval=30s --timeout=5s --start-period=300s --retries=3 \
    CMD curl -sf http://localhost:8080/ > /dev/null || exit 1

ENTRYPOINT ["/app/entrypoint.sh"]
