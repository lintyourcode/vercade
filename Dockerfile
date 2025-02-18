FROM python:3.11-slim

RUN apt-get update && apt-get install -y xvfb

ENV PYTHONUNBUFFERED 1
ENV POETRY_VERSION 1.8.3

RUN pip install "poetry==$POETRY_VERSION"

WORKDIR /app

COPY pyproject.toml poetry.lock ./

RUN poetry config virtualenvs.create false \
    && poetry install --no-interaction --no-ansi

COPY . .

RUN poetry run playwright install chromium
RUN poetry run playwright install-deps chromium

CMD ["poetry", "run", "xvfb-run", "-a", "python", "-m", "friendbot"]
