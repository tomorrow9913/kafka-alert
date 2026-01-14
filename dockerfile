# Use a multi-stage build to keep the final image small
FROM python:3.12-alpine AS builder

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

# Install dependencies using uv sync
# This creates a virtual environment in /app/.venv
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    uv sync --frozen --no-dev --no-install-project

# Final stage
FROM python:3.12-alpine

WORKDIR /app

# Copy the virtual environment from the builder
COPY --from=builder /app/.venv /app/.venv
COPY . /app

# Set environment variables to use the virtual environment
ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONUNBUFFERED=1

# Run the application
CMD ["python", "main.py"]