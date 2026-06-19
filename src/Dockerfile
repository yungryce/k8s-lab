# --- Stage 1: Build dependencies ---
FROM python:3.11-slim AS builder

WORKDIR /app

# Prevent Python from writing .pyc files and enable unbuffered logging
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Install build essentials if you have dependencies that require compilation
# RUN apt-get update && apt-get install -y --no-install-recommends gcc build-essential

COPY requirements.txt .

# Install dependencies to a local user directory
RUN pip install --no-cache-dir --user -r requirements.txt


# --- Stage 2: Final runtime image ---
FROM python:3.11-slim AS runtime

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH=/home/appuser/.local/bin:$PATH

# Create a non-root user for security compliance (Least Privilege)
RUN useradd --create-home appuser && chown -R appuser:appuser /app
USER appuser

# Copy installed dependencies from the builder stage
COPY --from=builder /root/.local /home/appuser/.local

# Copy application code (ensure ownership is set to the non-root user)
COPY --chown=appuser:appuser ./app /app/app

# Alembic config + migration scripts (needed for init container)
COPY --chown=appuser:appuser alembic.ini /app/
COPY --chown=appuser:appuser alembic /app/alembic

# Expose FastAPI's default port
EXPOSE 8000

# Run Uvicorn. 
# Note: In Kubernetes, bind to 0.0.0.0, and let K8s handle external access.
CMD ["uvicorn", "app.app:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]