# Dockerfile for Hikvision Recovery
# Multi-stage build for minimal production image

# =============================================================================
# Build Stage
# =============================================================================
FROM python:3.10-slim AS builder

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    libffi-dev \
    libssl-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY pyproject.toml setup.py requirements.txt ./
RUN pip install --no-cache-dir --upgrade pip setuptools wheel \
    && pip install --no-cache-dir build

# Copy source code
COPY hikvision_recovery/ ./hikvision_recovery/
COPY README.md ./

# Build package
RUN python -m build --sdist --wheel --outdir dist/

# =============================================================================
# Runtime Stage
# =============================================================================
FROM python:3.10-slim AS runtime

WORKDIR /app

# Install runtime dependencies only
RUN apt-get update && apt-get install -y --no-install-recommends \
    libffi-dev \
    libssl-dev \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN groupadd -r hikvision && useradd -r -g hikvision -m -d /app -s /bin/bash hikvision

# Copy built package from builder
COPY --from=builder /app/dist/ ./dist/

# Install package
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir dist/*.whl \
    && rm -rf dist/

# Set user
USER hikvision

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/home/hikvision/.local/bin:${PATH}"

# Default command
ENTRYPOINT ["hikvision"]
CMD ["--help"]

# Labels
LABEL org.opencontainers.image.title="Hikvision Recovery" \
      org.opencontainers.image.description="Professional Hikvision DVR/NVR ISAPI Client and HCNetSDK Wrapper" \
      org.opencontainers.image.version="0.2.0" \
      org.opencontainers.image.authors="Hikvision Recovery Team" \
      org.opencontainers.image.source="https://github.com/hikvision-recovery-ultimate" \
      org.opencontainers.image.licenses="MIT"