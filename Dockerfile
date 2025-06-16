FROM python:3.11-slim

RUN apt-get update && apt-get install -y git maven npm openjdk-17-jdk

ENV PYTHONUNBUFFERED 1
ENV POETRY_VERSION 1.8.3

RUN pip install "poetry==$POETRY_VERSION" uv

WORKDIR /app

RUN git clone https://github.com/SaseQ/discord-mcp.git discord-mcp \
    && cd discord-mcp \
    && mvn package

COPY pyproject.toml poetry.lock ./

RUN poetry config virtualenvs.create false \
    && poetry install --no-interaction --no-ansi

COPY . .

CMD ["poetry", "run", "python", "-m", "friendbot"]
