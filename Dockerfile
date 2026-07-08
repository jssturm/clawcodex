# ClawCodex Secure — Hardened Docker Image
# Multi-stage build for minimal attack surface

FROM python:3.12-slim AS builder
WORKDIR /build
COPY requirements-locked.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements-locked.txt

FROM python:3.12-slim AS runtime
LABEL org.opencontainers.image.title="clawcodex-secure"
LABEL org.opencontainers.image.description="Hardened ClawCodex MCP server for B2B fintech workflows"
LABEL org.opencontainers.image.source="https://github.com/jstur/clawcodex-secure"

# Create non-root user
RUN groupadd -r clawcodex -g 1000 && \
    useradd -r -g clawcodex -u 1000 -m -s /bin/bash clawcodex

# Install only runtime dependencies (no dev packages)
COPY --from=builder /install /usr/local

# Copy application
COPY --chown=clawcodex:clawcodex . /app
WORKDIR /app

# Read-only filesystem (writable /tmp only)
RUN chmod -R 555 /app && \
    chmod 755 /tmp && \
    chown -R clawcodex:clawcodex /tmp

# Drop all capabilities, no new privileges
# These are enforced at docker run time, declared here for documentation
# --cap-drop=ALL --security-opt=no-new-privileges --read-only --tmpfs /tmp

USER clawcodex

# Default: MCP stdio serve (no network needed)
ENTRYPOINT ["python3", "-m", "src.cli"]
CMD ["mcp", "serve"]