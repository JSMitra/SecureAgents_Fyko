# ── ANN Generator Dockerfile ─────────────────────────────────────────────────
FROM python:3.10-slim

# Non-root user
RUN groupadd --gid 1001 fyko \
 && useradd --uid 1001 --gid fyko --shell /bin/bash --create-home fyko

WORKDIR /app

# Install system-level build deps needed by some Python packages
RUN apt-get update \
 && apt-get install -y --no-install-recommends gcc libpq-dev \
 && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY worker.py ann_builder.py ./

RUN chown -R fyko:fyko /app

USER fyko

CMD ["python", "worker.py"]
