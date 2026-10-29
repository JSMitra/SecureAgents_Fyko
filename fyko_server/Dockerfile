# ── Fyko Server Dockerfile ──────────────────────────────────────────────────
FROM python:3.10-slim

# Non-root user
RUN groupadd --gid 1001 fyko \
 && useradd --uid 1001 --gid fyko --shell /bin/bash --create-home fyko

WORKDIR /app

# Install dependencies as root, then switch
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application source
COPY app/ ./app/

# Hand ownership to non-root user
RUN chown -R fyko:fyko /app

USER fyko

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
