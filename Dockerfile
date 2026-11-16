FROM node:22-bookworm-slim AS node
FROM python:3.12-slim-bookworm
RUN apt-get update && apt-get install -y --no-install-recommends libstdc++6 ca-certificates \
    && rm -rf /var/lib/apt/lists/*
COPY --from=node /usr/local/bin/node /usr/local/bin/node
COPY --from=node /usr/local/lib/node_modules /usr/local/lib/node_modules
RUN ln -s /usr/local/lib/node_modules/npm/bin/npm-cli.js /usr/local/bin/npm
WORKDIR /app
COPY requirements.txt package.json package-lock.json ./
RUN pip install --no-cache-dir -r requirements.txt && npm ci --omit=dev && npm cache clean --force
COPY studio ./studio
COPY reference ./reference
COPY data/synthetic.json ./data/synthetic.json
COPY scripts ./scripts
RUN useradd --create-home --uid 10001 studio && mkdir -p /var/lib/studio /var/cache/models \
    && chown -R studio:studio /app /var/lib/studio /var/cache/models
USER studio
ENV STUDIO_HOST=0.0.0.0 STUDIO_PORT=8088 STUDIO_DATA_DIR=/var/lib/studio HF_HOME=/var/cache/models
EXPOSE 8088
CMD ["python", "-m", "studio"]
