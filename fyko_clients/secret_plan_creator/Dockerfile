FROM python:3.10-slim

# ── System deps ───────────────────────────────────────────────────────────────
RUN apt-get update && apt-get install -y --no-install-recommends \
        gcc \
        libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# ── Non-root user ─────────────────────────────────────────────────────────────
RUN useradd --create-home --shell /bin/bash fyko
WORKDIR /app

# ── Python dependencies ───────────────────────────────────────────────────────
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

# ── Application code ──────────────────────────────────────────────────────────
COPY shared/           /app/shared/
COPY secret_plan_creator/ /app/secret_plan_creator/

# Add /app to PYTHONPATH so `from shared.xxx import ...` works
ENV PYTHONPATH=/app

# ── Runtime ───────────────────────────────────────────────────────────────────
USER fyko
EXPOSE 9001

# --app-dir adds /app/secret_plan_creator to sys.path, so:
#   • `from agent import ...`       resolves to /app/secret_plan_creator/agent.py  ✓
#   • `from shared.xxx import ...`  resolves via PYTHONPATH=/app                   ✓
CMD ["python", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "9001", "--app-dir", "/app/secret_plan_creator"]
