# Friendbot

> If you don't make friends, make enemies.

Friendbot is an LLM Discord bot that can:

* :white_check_mark: Adopt a personality
* :white_check_mark: Respond to messages
* :white_check_mark: React to messages with emojis
* :white_check_mark: Search the internet
* :white_check_mark: Store memories
* :white_check_mark: Optionally moderate messages

## Quick start

### Discord

1. Create a [Discord bot](https://discord.com/developers/docs/quick-start/getting-started).
2. Under "Bot", enable the "Message Content Intent" and "Server Members Intent" permissions.
3. Copy the bot token.

### Pinecone

Create a [Pinecone index](https://docs.pinecone.io/guides/get-started/overview).

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
poetry run python -m friendbot
```

To run the bot in a Docker container, run:

```sh
docker build -t friendbot .
docker run -d --env-file .env friendbot
```

Now, you should be able to invite the bot to your server and start chatting.

## Configuration

### Name

The `FRIENDBOT_NAME` environment variable is used to configure the bot's name. It must match the name of the Discord bot.

### Identity

The `FRIENDBOT_IDENTITY` environment variable is used to configure the bot's personality. A simple identity might look like this:

```
FRIENDBOT_IDENTITY="You are a funny, intelligent and creative AI Discord user named Sam."
```

More complex identities generally result in more interesting responses.

### Models

All [LiteLLM](https://docs.litellm.ai/docs/providers) models are supported.

* The `LLM` environment variable is used to configure the bot's language model.
* The `FRIENDBOT_WEB_LLM` environment variable is used to configure the bot's web language model.
* The `EMBEDDING_MODEL` environment variable is used to configure the bot's embedding model.

### Moderation

The `FRIENDBOT_MODERATE_MESSAGES` environment variable is used to configure the bot's moderation settings. If set to `true`, the bot will filter out messages that are flagged by the OpenAI moderation API when reading a channel's message history.

```
FRIENDBOT_MODERATE_MESSAGES=true
```
