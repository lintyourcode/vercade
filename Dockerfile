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


# Example image: adds Node.js and preinstalls the Discord MCP server pinned
# in mcp-template.json (keep the versions in sync), so the bot's `npx` call
# hits the local cache instead of downloading the package at startup (a cold
# download exceeds the MCP server initialization timeout). Build with
# `docker build --target example`.
FROM base AS example

RUN apt-get update && apt-get install -y nodejs npm \
    && npm install -y @quadslab.io/discord-mcp@2.1.1

CMD ["poetry", "run", "python", "-m", "vercade"]


# Production image. Kept last so `docker build` builds it by default and the
# test and example stages are skipped.
FROM base AS production

CMD ["poetry", "run", "python", "-m", "vercade"]
