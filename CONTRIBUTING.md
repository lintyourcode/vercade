# Contributing

<!-- TODO(#14): Document type checking once all type errors are fixed -->

Thanks for contributing to vercade!

## Getting started

1. Fork the repository
2. Clone your fork
3. Install dependencies: `poetry install`
4. Run tests: `poetry run pytest`
5. Make your changes
6. Lint and format: `poetry run ruff check . && poetry run ruff format .`
7. Run tests: `poetry run pytest`
8. Commit your changes: `git commit -m "feat: add new feature"`
9. Push your changes: `git push`
10. Open a pull request

Please use [conventional commits](https://www.conventionalcommits.org/en/v1.0.0/) for your commit messages

## Architecture

```mermaid
graph LR
    User -->|"Sends message"| DiscordClient
    DiscordClient -->|"Invokes"| Agent
    Schedule -->|"Invokes"| Agent
    Agent -->|"Uses MCP servers"| FastMCP
    FastMCP --> DiscordMCPServer
    FastMCP --> WebBrowsingMCPServer
    FastMCP --> OtherUserProvidedMCPServer
```

**Tech stack:**

* Python 3.11+
* [Discord.py](https://discordpy.readthedocs.io) listens for new messages
* [LiteLLM](https://docs.litellm.ai/docs/#basic-usage) calls LLMs
* [FastMCP](https://gofastmcp.com) provides an MCP client

**Core components:**

* **Discord client**: Discord bot that listens for new messages
* **Trigger**: Invokes the agent both when a message is received and on a schedule
* **Agent**: LLM agent that can use the user-provided MCP servers

## End-to-end tests

The end-to-end suite runs the real bot (as a subprocess) plus a user-stub bot that plays the end user, both connected to a persistent Discord test server. The tests are marked `e2e` and skip automatically when credentials are missing.

**Prerequisites:**

* A second Discord bot token for the user stub
* **Message Content intent enabled in the [Discord Developer Portal](https://discord.com/developers/applications) for both bots** — the stub needs it to read replies, and the `discord-mcp-plus` MCP server needs it to read messages
* Node.js with `npx` on your `PATH`
* `OPENAI_API_KEY` set in `.env`

Set `VERCADE_E2E_USER_STUB_TOKEN` and `VERCADE_E2E_GUILD_ID` in `.env` (see `template.env`).

**One-time setup:**

Discord bots cannot create servers, so create the test server manually once (suggested name: `vercade-e2e`) and set `VERCADE_E2E_GUILD_ID` to its ID (Developer Mode > right-click the server > Copy Server ID). Then run:

```
poetry run python -m tests.e2e.setup_server
```

The script prints an invite link (server pre-selected) for any bot that has not joined yet or is missing permissions, and waits until both bots are fully set up. The links request exactly the permissions each bot needs; re-opening one for a bot that already joined updates its permissions. Re-runs skip whatever is already done.

**Run:**

```
poetry run pytest tests/e2e -q
```

The first run downloads the MCP package via `npx` and can take a few minutes.
