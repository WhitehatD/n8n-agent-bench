# The agent's box: n8n's toolchain, no secrets, no route out except the egress proxy.
FROM node:24-bookworm
RUN npm i -g pnpm@12.4.2 \
 && apt-get update && apt-get install -y --no-install-recommends git ripgrep python3 \
 && rm -rf /var/lib/apt/lists/*
RUN useradd -m -u 1001 agent && mkdir -p /pnpm-store /work && chown agent /pnpm-store /work
USER agent
ENV HTTPS_PROXY=http://egress:8080 HTTP_PROXY=http://egress:8080 NO_PROXY=egress \
    npm_config_store_dir=/pnpm-store CI=true N8N_DIAGNOSTICS_ENABLED=false
WORKDIR /work
