# Multi-stage Python build configuration
FROM python:3.11-slim AS builder

WORKDIR /app

# Install build dependencies for libraries (scipy/scikit-learn compile steps)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Install python dependencies in a virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Final stage runner image
FROM python:3.11-slim AS runner

WORKDIR /app

# Copy virtualenv and dependencies from builder stage
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy backend app codebase
COPY . .

EXPOSE 8000

ENV APP_ENV=production
ENV DEBUG=False

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
