FROM python:3.11-slim AS base

RUN apt-get update && apt-get install -y git build-essential

ENV PYTHONUNBUFFERED 1
# TODO: Update Poetry to latest version
ENV POETRY_VERSION 1.8.3

RUN pip install "poetry==$POETRY_VERSION" uv


WORKDIR /app

COPY pyproject.toml poetry.lock ./

RUN poetry config virtualenvs.create false \
    && poetry install --no-interaction --no-ansi --no-root

COPY . .

RUN poetry install --no-interaction --no-ansi --only-root


# Test image: adds Node.js so the end-to-end tests can launch the Discord
# MCP server with npx. Build with `docker build --target test`.
FROM base AS test

RUN apt-get update && apt-get install -y nodejs npm

CMD ["poetry", "run", "pytest", "-q"]


# Production image. Kept last so `docker build` builds it by default and the
# test stage is skipped.
FROM base AS production

CMD ["poetry", "run", "python", "-m", "vercade"]
