# Drizzle-NEO llama-swap Configuration

This directory contains instructions on setting up a locally hosted llama-swap
instance in a podman/docker environment.

## Usage

- Download your desired models and place them into their respective directories
  in the `models` directory
  - see: comments in `config.yaml`
- Edit `compose.yml` and replace the placeholder volume paths with your own
- Edit `config.json` and replace the model names there with the models you want
  to use
  - see: `config.yaml` for appropriate model names
- Make sure you are inside the `llama-swap` directory
- Run the following command: `$ podman compose up` 
  - Replace `podman` with `docker` depending on which one you use
- Set server.url in `config.json` to "http://127.0.0.1:9292/v1"

## Preconfigured Models

More detailed documentation (required RAM/VRAM, download links, etc.) and
configuration options for models are detailed in `config.yaml`.

`config.yaml` contains 3 preconfigured models; GPT-OSS-20B (both medium and high
reasoning, highest quality), Qwen3 (thinking and instruct versions, medium
quality) and Granite-4.0-h-Tiny (fastest, low quality).

GPT-OSS-20B is designed to run on a 16GB VRAM GPU, but since it is a MoE
(mixture-of-experts) model, it may run at decent speeds on even 8GB GPUs by
adjusting the `-ncmoe` configuration option. If you want to run GPT-OSS-20B on
your CPU, set `-ngl` to 0. Running GPT-OSS-20B on CPU requires 16GB RAM at
minimum.

Qwen3-4B (thinking and instruct) is designed to run on low-VRAM GPUs. I suggest
starting with the thinking version (higher quality) and moving to the instruct
version if thinking is too slow (Qwen3 is known to overthink at times). Qwen3-4B
is slower when running on CPU than GPT-OSS-20B and much worse quality, so it
should **only** be used if you have less than 16GB RAM and no dedicated GPU.

Granite 4.0 Tiny is designed to run on a CPU, thus its `-ngl` is set to 0 by
default. It is the fastest model of the three, but also the lowest quality.

## Troubleshooting

### Model takes long to respond!

Open the UI in `http://127.0.0.1:9292`, switch to the "Models" tab and observe
the upstream logs for any errors.

If the model is still processing the prompt, it should have a line containing
something similar to this:
`slot update_slots: id  3 | task 0 | prompt processing progress, n_tokens = 2048, batch.n_tokens = 2048, progress = 0.891986`

In this case, wait patiently for the prompt to be processed and a response to be
generated (no progress reports on generation). Prompt processing is notoriously
slow on CPU.

llama.cpp (the underlying program llama-swap uses to run models) is fairly
optimal at caching prompts, so only the first response after loading the model
should be take a while, with subsequent prompts relying mostly only on
generation speed.

In case the time to process the prompt takes too long, switch to a smaller model
or decrease the value of `memory.max_messages` in `config.json` to decrease the
maximum amount of messages processed.
