FROM python:3.11-slim

# TODO(#25): Remove curl along with nvm
RUN apt-get update && apt-get install -y curl git build-essential

ENV PYTHONUNBUFFERED 1
# TODO: Update Poetry to latest version
ENV POETRY_VERSION 1.8.3

RUN pip install "poetry==$POETRY_VERSION" uv

# TODO(#25): Remove nvm
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
