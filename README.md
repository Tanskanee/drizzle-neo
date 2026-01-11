# Drizzle-NEO

## Drizzle AI - Uusi ääni kasvista! 🌿💬

**Drizzle AI:n uudella teknologialla voit kuulla kasvien tarinoita.** 🌱

Vuodesta toiseen, teemme työtasi, meidän kasvavat! Nyt voit kuulla nekin!
AI-teknologia yhdistää sinut ja kasvien maailmaan, luodaksesi uuden luovaa
yhteyttä luonnon kanssa. Drizzle AI:n avulla saat tietoa kasvin tarinoista,
jotka kertovat häiriöistä tai tarvitsemuksesta. 

**Mitä tämä tarkoittaa?**

* Tieto riippuu kasvien väriin ja kasvustoon.
* Kuulet kasvien tarinoita, jotka kertovat häiriöistä tai tarvitsemuksesta. 
* Tulet luomaan uusia ja vastuullisia ympäristön tasapainotuksia.  

**Oletko valmis luomaan uuden maailman kasviin?** 

_Toivoisitteeko kokeilemaan Drizzle AI:tä?_

## Introduction

Drizzle NEO is a version of Drizzle AI that remembers past conversations, is
able to call tools, has long-term memory, etc. (more features listed below) It
can be seen as a continuation to my previous IoT project, which was a fairly
rudimentary system that generated a single message based on a plant's moisure
level, with no memory or anything else fancy.

## Warnings!

This project has only been tested on Linux. It may or may not work inside WSL2.

Additionally, it has only been tested using a locally hosted llama-swap instance
inside my LAN. This project should work with any OpenAI-compatible endpoint
(ChatGPT, Gemini, etc.), but that is not guaranteed. Instructions and
configurations for setting up a llama-swap server are included inside
`./llama-swap`.

## Features

- Conversation (short-term memory) history (stored in context.txt)
- Automatic pruning and archival of conversation history
- Long-term memory via memory generation (stored in memory.txt) and RAG (from
  archived conversations in `context-archive.json`)
- Tool use via the MCP protocol
- Text-to-speech (hosted externally)
- Speech-to-text hands-free conversations using pywhispercpp

## Installation

- Set up a venv and activate it
  - `$ python -m venv venv`
  - `$ source venv/bin/activate`
- Install dependencies
  - `$ pip install -r requirements.txt --extra-index-url https://download.pytorch.org/whl/cpu`
  - WARNING! May require Python3 development headers! Install the appropriate
    package depending on your distribution (`python3-dev`, `python3-devel`,
    etc.). A C++ compiler (`g++`) may also be required.

## Usage

- Set your desired parameters in `config.json`
  - OpenAI-compatible API URL
  - Model for conversations and memory generation
  - MCP server URL (leave as default if running locally)
- Start the MCP server: `$ python mcp-server.py`
- Prompt model to confirm it is working: `$ python prompt.py -p "How are you?"`
  - Run `$ python prompt.py -h` for available options
- Run assistant.py for hands-free conversations: `$ python assistant.py`
  - Downloading the speech-to-text model may take a while
  - You should adjust the speech-to-text model based on your CPU, see comments
    in `assistant.py`
- If your API requires an API key, prepend it to the commands, for example:
  - `$ OPENAI_API_KEY="my-api-key" python prompt.py ...`
  - `$ OPENAI_API_KEY="my-api-key" python assistant.py`

For instructions on setting up your own llama-swap server, refer to `./llama-swap/README.md`.

## Configuration Options

Configuration options are stored in config.json.

### server.url

The OpenAI-compatible API's URL

### mcp.url

The MCP server's URL

### model

#### model

The conversation model. Tested with GPT-OSS, Qwen3 and Granite 4.0. The model
must support tool calls

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

## Implemented Tools

### get_moisture_levels

Returns a random value between 0% and 100%. Intended to simulate a real moisture
sensor in a potted plant's soil

### get_date_and_time

Returns the current date and time

### get_weather

Returns the current temperature and precipitation amount using `wttr.in`. This
service is down quite often, so expect curl errors

### recall_longterm_memory

Use RAG to recall information from past conversations. All conversations are
permanently stored in `context-archive.json`
