# Drizzle-NEO llama-swap Configuration

This directory contains instructions on setting up a locally hosted llama-swap
insance in a podman/docker environment.

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

## Preconfigured Models

More detailed documentation (required RAM/VRAM, download links, etc.) and
configuration options for models are detailed in `config.yaml`.

`config.yaml` contains 3 preconfigured models; GPT-OSS-20B (both medium and high
reasoning, highest quality), Qwen3 (thinking and instruct versions, medium
quality) and Granite-4.0-h-Tiny (fastest, low quality).

GPT-OSS-20B is designed to run on a 16GB GPU, but since it is a MoE
(mixture-of-experts) model, it may run at decent speeds on even 8GB GPUs by
adjusting the `-ncmoe` configuration option. If you want to run GPT-OSS on your
CPU, set `-ngl` to 0.

Qwen3 (thinking and instruct) are designed to run on CPU, thus `-ngl` is set to
0 by default. I suggest starting with the thinking version (higher quality) and
moving to the instruct version if thinking is too slow (Qwen3 is known to
overthink at times).

Granite 4.0 Tiny is also designed to run on a CPU. It is the fastest model of
the three, but also the lowest quality.
