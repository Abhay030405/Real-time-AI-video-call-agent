# Vaani agent image.
# Used for local running (docker-compose.yml) and for deploying to
# LiveKit Cloud in the Mumbai region.
# Build from the repository root:  docker build -f agent/Dockerfile .
#
# Expects (created in Phase 0/1): agent/pyproject.toml, agent/uv.lock,
# and an entry point agent/main.py, following LiveKit's Python agent starter.

FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

# uv installs Python packages quickly and reproducibly from the lock file
COPY --from=ghcr.io/astral-sh/uv:0.5.11 /uv /usr/local/bin/uv

# Run as a normal user, not root
RUN useradd --create-home --uid 10001 vaani
WORKDIR /app

# Install packages first so this layer is reused when only code changes
COPY agent/pyproject.toml agent/uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

# Our code, Vaani's prompts and her pre-recorded clips
COPY agent/ ./
COPY assets/audio/ ./assets/audio/
RUN uv sync --frozen --no-dev

# Download model files the agent needs at start (for example LiveKit's
# turn detector), so calls don't wait for a download
RUN uv run main.py download-files

USER vaani
CMD ["uv", "run", "main.py", "start"]
