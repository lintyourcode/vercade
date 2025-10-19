# Repository Guidelines

## Project Structure & Module Organization
- `vercade/` — Python package.
  - `agent.py` LLM agent that can call MCP tools.
  - `discord.py` Discord client adapting the platform to `SocialMedia`.
  - `trigger.py` schedules background work and reacts to messages.
  - `social_media.py` shared data models and interfaces.
  - `__main__.py` entrypoint (`python -m vercade`).
- `tests/` — pytest suite; `conftest.py` provides a minimal in‑process MCP for tests.
- `.github/workflows/check-code.yml` — CI: ruff lint/format + pytest on 3.11/3.12.
- `pyproject.toml` — Poetry config, dependencies, pytest settings.
- `Dockerfile` — container image to run the bot.

## Build, Test, and Development Commands
- Install deps: `poetry install`
- Run locally: `poetry run python -m vercade`
- Lint: `poetry run ruff check .`
- Format: `poetry run ruff format .`
- Type check (best‑effort): `poetry run mypy vercade`
- Tests: `poetry run pytest -q` (subset: `pytest -k name -q`)
- Docker: `docker build -t vercade . && docker run --env-file .env --init --privileged vercade`

## Coding Style & Naming Conventions
- Python 3.11, 4‑space indent, type hints encouraged in new/modified code.
- Names: modules/functions `snake_case`, classes `PascalCase`, constants `UPPER_CASE`.
- Keep async flows consistent with existing patterns (e.g., `asyncio.create_task`, callbacks in `SocialMedia`).
- Use ruff for both linting and formatting; commits should be ruff‑clean.

## Testing Guidelines
- Frameworks: `pytest`, `pytest-asyncio` (asyncio mode is auto via `pyproject.toml`).
- Test layout: files under `tests/test_*.py`; place shared helpers in `tests/conftest.py`.
- Environment: some tests call LLMs; export `OPENAI_API_KEY` (CI uses a secret).
- Prefer unit tests that mock external services; use the provided LocalDiscordMcp when practical.

## Commit & Pull Request Guidelines
- Follow Conventional Commits: `feat(agent): …`, `fix(discord): …`, `refactor(trigger): …`.
- Keep commit headers concise (≤ 50 chars), imperative mood, optional scope; move details to the body and use footers.
- Link issues via commit footers: use `Closes: #123` when the change resolves the issue, or `Refs: #123` when it only references it.
- PRs must: describe the change, pass CI, and include screenshots/log snippets when user‑visible behavior changes.
- Docs policy: update `README.md` only with user‑facing changes; update `CONTRIBUTING.md` for technical/architectural changes; keep `AGENTS.md` in sync when guidelines change.

## Security & Configuration Tips
- Never commit real tokens. Start from `template.env` → `.env`; set `DISCORD_TOKEN`, `VERCADE_NAME`, `VERCADE_IDENTITY`, `VERCADE_LLM`, and optional `VERCADE_LLM_TEMPERATURE`/`VERCADE_LLM_REASONING_EFFORT`.
- To enable MCP tools, set `MCP_PATH` to a JSON config; environment values beginning with `$` are expanded from your shell.
