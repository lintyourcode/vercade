FROM python:3.11-slim

RUN apt-get update && apt-get install -y curl git

ENV PYTHONUNBUFFERED 1
ENV POETRY_VERSION 1.8.3

RUN pip install "poetry==$POETRY_VERSION" uv

RUN curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.40.3/install.sh | bash \
    && . "$HOME/.nvm/nvm.sh" \
    && nvm install 24 \
    && nvm alias default 24 \
    && ln -s $(command -v node) /usr/local/bin/node \
    && ln -s $(command -v npm) /usr/local/bin/npm \
    && ln -s $(command -v npx) /usr/local/bin/npx

WORKDIR /app

COPY pyproject.toml poetry.lock ./

RUN poetry config virtualenvs.create false \
    && poetry install --no-interaction --no-ansi

COPY . .

CMD ["poetry", "run", "python", "-m", "friendbot"]
