# Repository Guidelines

## Project Structure
- `vercade/` — Python package.
  - `agent.py` LLM agent that can call MCP tools.
  - `discord.py` Discord client adapting the platform to the `SocialMedia` interface.
  - `trigger.py` invokes the agent on a schedule or in response to a message.
  - `social_media.py` shared data models and interfaces.
  - `__main__.py` entrypoint (`python -m vercade`).
- `tests/` — pytest suite.
  - `e2e/` — end‑to‑end tests.
- `.github/workflows/check-code.yml` — CI: ruff lint/format + pytest on 3.11/3.12.
- `pyproject.toml` — Poetry config, dependencies, pytest settings.
- `Dockerfile` — container image to run the bot.

## Development Commands
- Install deps: `poetry install`
- Run locally: `poetry run python -m vercade`
- Lint: `poetry run ruff check .`
- Format: `poetry run ruff format .`
- Type check (best‑effort): `poetry run mypy vercade`
- Tests: `poetry run pytest -q` (subset: `pytest -k name -q`)
- Docker: `docker build -t vercade . && docker run --env-file .env --init --privileged vercade`

## Style Guidelines
- Python 3.11-3.13, 4‑space indent, type hints encouraged.
- Naming: modules/functions `snake_case`, classes `PascalCase`, constants `UPPER_CASE`.
- Keep async flows consistent with existing patterns (e.g., `asyncio.create_task`, callbacks in `SocialMedia`).
- Use ruff for both linting and formatting; commits should be ruff‑clean.

## Testing Guidelines
- Frameworks: `pytest`, `pytest-asyncio` (asyncio mode is auto via `pyproject.toml`).
- Test layout: unit tests in `tests/test_*.py`, end‑to‑end tests in `tests/e2e/test_*.py`; place shared helpers in `tests/conftest.py` or `tests/e2e/conftest.py`.
- Environment: some tests call LLMs; export `OPENAI_API_KEY` (CI uses a secret).

## Commit Guidelines
- Follow Conventional Commits: `feat(agent): …`, `fix(discord): …`, `refactor(trigger): …`.
- Keep commit headers concise (≤ 50 chars), imperative mood, optional scope; move details to the body and use footers.
- Link issues via commit footers: use `Closes: #123` when the change resolves the issue, or `Refs: #123` when it only references it.
- Commits must describe the change and any impact on the user. They must pass CI.
- Docs policy: update `README.md` only with user‑facing changes; update `CONTRIBUTING.md` for technical/architectural changes; keep `AGENTS.md` in sync when guidelines change.

## Security
- Never commit real tokens. Start from `template.env` → `.env`; set `DISCORD_TOKEN`, `VERCADE_NAME`, `VERCADE_IDENTITY`, `VERCADE_LLM`, and optional `VERCADE_LLM_TEMPERATURE`/`VERCADE_LLM_REASONING_EFFORT`.
