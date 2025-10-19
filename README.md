# Vercade

[![Discord](https://img.shields.io/badge/Discord-5865F2?style=flat&logo=discord&logoColor=white)](https://discord.gg/4fcsGm9sqj)

Vercade is a Discord bot that can:

* :white_check_mark: Adopt a personality
* :white_check_mark: Respond to messages with an LLM
* :white_check_mark: Reason
* :white_check_mark: Use MCP servers to integrate with other services

When setting up vercade, you'll attach it to a Discord bot and add the bot to some servers. Whenever a message is sent in a server, vercade will invoke an LLM agent. The agent has access to whichever MCP servers you've configured. It will call whichever tools it needs to, based on a system prompt.

## Quick start

### Discord

1. Create a [Discord bot](https://discord.com/developers/docs/quick-start/getting-started).
2. Under "Bot", enable the "Message Content Intent" and "Server Members Intent" permissions.
3. Copy the bot token.

### Installation

Clone this repo and run:

```sh
poetry install
cp template.env .env
$EDITOR .env
```

### Running

To start up your bot, run:

```sh
poetry run python -m vercade
```

To run the bot in a Docker container, run:

```sh
docker build -t vercade .
docker run --init --privileged vercade
```

Now, you should be able to invite the bot to your server and start chatting.

## Configuration

### Name

The `VERCADE_NAME` environment variable is used to configure the bot's name. It must match the name of the Discord bot.

### Identity

The `VERCADE_IDENTITY` environment variable is used to configure the bot's personality and behavior. A simple identity might look like this:

```
VERCADE_IDENTITY="You are a funny, intelligent and creative AI Discord user named Sam."
```

More complex identities generally result in more interesting responses.

### Activity

The `VERCADE_ACTIVITY` environment variable can be used to configure the bot's initial presence. It must be a string.

```
VERCADE_ACTIVITY="Ping me!"
```

### Models

The `VERCADE_LLM` environment variable is used to configure the bot's language model. All [LiteLLM](https://docs.litellm.ai/docs/providers) models are supported.
* The `VERCADE_LLM_TEMPERATURE` environment variable is used to configure the LLM's temperature.
* The `VERCADE_LLM_REASONING_EFFORT` environment variable is used to configure the LLM's reasoning effort (e.g. "low", "medium", "high").

### Scheduling

Use `VERCADE_SCHEDULE_INTERVAL` to control background, scheduled agent execution. The agent will always respond when messaged regardless of this setting.

- **Default**: `1h` (one hour)
- **Disable**: set to `off`, `false`, `disabled`, `none`, `no`, or `0`
- **Formats**:
  - Plain seconds: `300`
  - With suffix: `45s`, `15m`, `2h`

### MCP Servers

The `MCP_PATH` environment variable is used to configure the bot's MCP servers. It should be the path to a Claude MCP JSON config file. MCP server environment variables beginning with `$` are resolved to the corresponding environment variables.

```
MCP_PATH=mcp.json
```

**Required MCP Servers:**

* A Discord MCP server ([example](https://github.com/SaseQ/discord-mcp))

**mcp.json**

```json
{
  "mcpServers": {
    "discord": {
      "command": "java",
      "args": ["-jar", "/path/to/discord-mcp.jar"],
      "env": {
        "DISCORD_TOKEN": "$DISCORD_TOKEN"
      }
    }
  }
}
```

### Logging

The `VERCADE_LOG_LEVEL` environment variable is used to configure the bot's logging level. It must be one of: `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL` (default: `WARNING`).

```
VERCADE_LOG_LEVEL=WARNING
```

### Contributing

Please see [CONTRIBUTING.md](CONTRIBUTING.md)

### License

Vercade is open source software released under the [GNU General Public License v3.0](LICENSE).
