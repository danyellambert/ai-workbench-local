FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PPT_CREATOR_RUNTIME_MODE=docker_container \
    PPT_CREATOR_API_HOST=0.0.0.0 \
    PPT_CREATOR_API_PORT=8787 \
    PPT_CREATOR_API_ASSET_ROOT=/app/examples

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        ghostscript \
        libreoffice-impress \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml README.md /app/
COPY ppt_creator /app/ppt_creator
COPY ppt_creator_ai /app/ppt_creator_ai
COPY examples /app/examples
COPY bin /app/bin

RUN pip install --no-cache-dir .

WORKDIR /work

EXPOSE 8787

CMD ["bash", "/app/bin/run_ppt_creator_api_container.sh"]
