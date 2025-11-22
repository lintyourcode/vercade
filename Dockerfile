FROM python:3.11-slim

RUN apt-get update && apt-get install -y git build-essential

ENV PYTHONUNBUFFERED 1
# TODO: Update Poetry to latest version
ENV POETRY_VERSION 1.8.3

RUN pip install "poetry==$POETRY_VERSION" uv


WORKDIR /app

COPY pyproject.toml poetry.lock ./

RUN poetry config virtualenvs.create false \
    && poetry install --no-interaction --no-ansi

COPY . .

CMD ["poetry", "run", "python", "-m", "vercade"]
