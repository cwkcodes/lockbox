# Ingestion / canonical-build worker. Not built in the authoring environment (no Docker daemon); the package installs
# with `pip install .` and its test-suite passes against a PostGIS 16 database.
FROM python:3.12-slim
WORKDIR /app
ENV PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1
COPY ingest/pyproject.toml ./ingest/pyproject.toml
COPY ingest/atlas_ingest ./ingest/atlas_ingest
RUN pip install ./ingest
COPY db ./db
COPY scripts ./scripts
# raw downloads are cached here and must be on a volume (they are the immutable raw layer's on-disk copy)
ENV ATLAS_DATA_DIR=/data/raw
VOLUME /data
ENTRYPOINT ["atlas-ingest"]
CMD ["worker"]
