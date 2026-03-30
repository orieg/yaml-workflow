FROM python:3.12-slim

LABEL org.opencontainers.image.source="https://github.com/orieg/yaml-workflow"
LABEL org.opencontainers.image.description="Lightweight workflow engine for CI/CD pipelines, data processing, and DevOps automation"
LABEL org.opencontainers.image.licenses="MIT"

WORKDIR /app

# Install yaml-workflow with serve dependencies
RUN pip install --no-cache-dir 'yaml-workflow[serve]'

# Create default directories
RUN mkdir -p /app/workflows /app/runs

# Default: serve mode (web dashboard)
EXPOSE 8080
ENTRYPOINT ["yaml-workflow"]
CMD ["serve", "--host", "0.0.0.0", "--port", "8080", "--dir", "/app/workflows", "--base-dir", "/app/runs"]
