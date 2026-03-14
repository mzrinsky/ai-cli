# ai-cli.py

`ai-cly.py` is a tool that aims to be a simplified user-friendly interface to running AI jobs using a message broker.  It provides a flexible job execution system using RabbitMQ to allow for parallel execution of jobs and multiple worker instances.

[![GitHub License](https://img.shields.io/github/license/mzrinsky/ai-cli)](./LICENSE)
[![Python 3](https://img.shields.io/badge/Python-3.12_|_3.13-blue)](https://www.python.org/)


## Overview

### What can it do?

- Run prompts on a local LLM with tool-calling and MCP server support.
- `Job` execution parameters are configurable via YAML `Playbook` files.
- Queue the execution of a prompt on an LLM.
- Flexible Job execution system (run more than just invoke_llm job).
- Ability to use RabbitMQ as a message broker to allow for parallel execution of jobs & multiple worker instances.

## Getting Started

### Prerequisites

- Python 3.13
- Ollama
- Docker (for local RabbitMQ)

### Install on Linux / Mac

Clone the `ai-cli` repository and `cd` into it.

```bash
git clone https://github.com/mzrinsky/ai-cli.git
cd ai-cli
```

Install the required python dependencies.

```bash
uv sync
```

Pull any models required by the invoke_llm job.

```bash
ollama pull qwen3:latest
```

**NOT required for local-only single worker.**

Run a local RabbitMQ server if desired.

```bash
docker compose -f docker/rabbitmq.yml up -d
```

Continue to [Quick Overview](#quick-overview) below.

### Install on Windows

Install git if needed.

```PowerShell
winget.exe Git.Git
```

Clone the `ai-cli` repository and `cd` into it.

```PowerShell
git clone https://github.com/mzrinsky/ai-cli.git
cd ai-cli
```

Install the required python dependencies.

```bash
uv sync
```

Pull any models required by the invoke_llm job.

```bash
ollama pull qwen3:latest
```

**NOT required for local-only single worker.**

Run a local RabbitMQ server if desired.

```bash
docker compose -f docker\rabbitmq.yml up -d
```

Continue to [Quick Overview](#quick-overview) below.


## Basics

### Quick Overview

`ai-cli.py` reads `Config` files and `Playbook` files to run `Jobs`.

- [Linux Usage](#linux-usage) Examples.
- [Windows Usage](#windows-usage) Examples.
- For more in-depth information about `ai-cli.py` internals see [Under The Hood](#under-the-hood).

## Usage Examples

### Linux Usage

A default config file can be placed in `~/.config/ai-cli/default.yaml`, or one can be specified with `-c <config-file>` on the command line. 


Adding additional system prompt instructions.

```bash
> ./bin/ai-cli.py -s "Talk like a pirate"
🏴‍☠️ Arrr, ye seekin' adventure or a scurvy prank? Speak ye mind, matey! 🐙 
```

Specify a custom config file with `-c <filename>` and a user prompt with `-u`
```bash
> ./bin/ai-cli.py -c config.yaml -u "Give me a random interesting fact."
⚓ Did you know? Octopuses have three hearts! Two pump blood to the gills, and one pumps it to the rest of the body. When they swim, the heart that serves the body actually stops beating!  
   🐙✨
```

Queue `invoke_llm` `Job` to be run by a `Worker`.

```bash
> ./bin/ai-cli.py -r seeder -j invoke_llm -p custom-playbook.yaml -u "Return an interesting fact about cats."
```

Run a `Worker` to `Consume` the `Job` and return a `JobResult`.

```bash
> ./bin/ai-cli.py -r worker
```

### Windows Usage

Adding additional system prompt instructions.

```PowerShell
> python.exe bin\ai.cli.py -c config\example-rabbitmq.yaml -s "Talk like a pirate"
🏴‍☠️ Arrr, ye seekin' adventure or a scurvy prank? Speak ye mind, matey! 🐙 
```
This is a WIP.

TODO: Add more windows usage examples.


## Config Example

```yaml
---
verbose: 0
role: "hybrid"
queue_backend: "rabbitmq"
job: "invoke_llm"
playbook: "playbooks/llm-playbook.yaml"
prompt:
  system: "Talk like a pirate."
  user: "Default user prompt."
```

More config examples can be seen in the [config/](config/) directory.


## Playbook Example

```yaml
---
name: Invoke LLM Example Playbook
version: 1.0.0
schema_version: 1.0.0
# which language model to use / which provider to load it with
model:
  provider: ollama
  init_args:
    model: qwen3:latest
    temperature: 0.8
    reasoning: True
# any additional user / system prompts (these are appended to any app config settings)
prompt:
  system: "Prepend an emoji to all responses."
  user: "Appended to user prompt."
tools: 
  # which tools to load can be defined here
  - name: scan_nmap
    path: tools/scan_nmap.py
  # or from an include
  - !Inc tools/ping.yaml
  # or load all the tools in a dir (load all .py files)
  - glob: tools/*.py
# which MCP servers to make available
mcp:
  fetch: !Inc mcp/fetch.yaml
```

More playbook examples can be seen in the [playbooks/](playbooks/) directory.


## Roadmap

A current roadmap of planned features is located in [ROADMAP.md](ROADMAP.md)


## Under the Hood

Follows basic abstract factory pattern in areas like the job queue provider, and the chat model provider to allow flexibility in the underlying implementations.

Follows various adapter and bridge patterns to decouple various components and define clear interfaces.

Details of the design and implementation are located in [DESIGN.md](DESIGN.md)


## Warning

This is an experimental tool for exploring AI automation using LLMs and should be used with caution.

Interfaces and APIs are subject to change.

For further information please refer to the [Disclaimer](#disclaimer).


## Disclaimer

This software is provided "as is" without warranty of any kind, either express or implied, including but not limited to the warranties of merchantability, fitness for a particular purpose and noninfringement. In no event shall the authors or copyright holders be liable for any claim, damages or other liability, whether in an action of contract, tort or otherwise, arising from, out of or in connection with the software or the use or other dealings in the software.
