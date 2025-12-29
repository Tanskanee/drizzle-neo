# Drizzle-NEO

A version of Drizzle AI that remembers past conversations and has long-term
memory.

WARNING! This project has only been tested on Linux. It may or may not work
inside WSL2.

WARNING! This projecr has been only tested using a locally hosted llama-swap
instance inside my LAN, not protected by an API key. This project may work with
any other OpenAI-compatible endpoint (ChatGPT, Gemini, etc.), but it is not
quaranteed. Instructions for setting up a llama-swap server are included inside
`./llama-swap`.

## Features

- Conversation history (stored in context.txt)
- Automatic pruning of conversation history
- Long-term memory generation (stored in memory.txt)
- Tool use via the MCP protocol
- Text-to-speech (hosted externally)
- Speech-to-text using pywhispercpp

## Installation

- Set up a venv and activate it
  - `$ python -m venv venv`
  - `$ source venv/bin/activate`
- Install dependencies
  - `$ pip install -r requirements.txt`
  - WARNING! May require Python3 development headers! Install the appropriate
    package depending on your distribution (`python3-dev`, `python3-devel`, etc.).

## Usage

- Set your desired parameters in `config.json`
  - OpenAI-compatible API URL
  - Model for conversations and memory generation
  - MCP server URL (leave as default if running locally)
- Start the MCP server: `$ python server.py`
- Prompt model to confirm it is working: `$ python prompt.py -p "How are you?"`
  - Run `$ python prompt.py -h` for available options
- Run assistant.py for hands-free conversations: `$ python assistan.py`
  - Downloading the speech-to-text may take a while
  - You should adjust the speech-to-text model based on your CPU, see comments
    in `assistant.py`
- If your API requires an API key, prepend it to the commands, for exmaple:
  - `$ OPENAI_API_KEY="my-api-key" python prompt.py ...`
  - `$ OPENAI_API_KEY="my-api-key" python assistant.py`

## Configuration

Configuration options are stored in config.json

### server.url

The OpenAI-compatible API's endpoint

### mcp.url

The MCP server's URL

### model

#### model

The conversation model. Tested with GPT-OSS, Qwen3 and Granite 4.0. The model
must support tool calls.

#### prompt1

The format the LLM should answer in and what it must avoid

#### prompt2

The LLM's personality

#### prompt3

Information about the speech-to-text feature

### memory

#### model

The model used for summarizing the conversation and creating/updating long-term
memory (memory.txt). This model should be smarter than the conversation model.
GPT-OSS with high reasoning effort works well

#### prompt

The prompt used for memory generation

#### max_messages

The maximum amount of messages before long-term memory generation is triggered and the
conversation (context.txt) is trimmed to max_messages/2 messages
