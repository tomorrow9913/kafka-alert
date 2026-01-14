FROM python:3.12-alpine

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

# Install dependencies
# Using --system to install into the system python since it's a container
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=requirements.txt,target=requirements.txt \
    uv pip install --system -r requirements.txt

# Add the rest of the application
ADD . /app

# Run the application
CMD ["python", "main.py"]