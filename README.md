# ai-cli.py

> Aims to be a simplified user-friendly interface to running AI enabled jobs from the command line with the ability to queue executions.

This tool was created as part of my personal research and to serve as a basis for future work and testing.

It is currently a Work In Progress.

[![GitHub License](https://img.shields.io/github/license/mzrinsky/ai-cli)](./LICENSE)
[![Python 3](https://img.shields.io/badge/Python-3.12_|_3.13-blue)](https://www.python.org/)


## Warning

This is an experimental tool for exploring AI automation using LLMs and should be used with caution.

Interfaces and APIs are subject to change.

For further information please refer to the [Disclaimer](#disclaimer).


## Overview

### What is it?

`ai-cli.py` is a tool that aims to be a simplified user-friendly interface to running AI enabled jobs from the command line.

### What can it do?

- Run user prompts on a an LLM with tool-calling and MCP server support.
- Job execution parameters are configurable via YAML files.
- Queue the execution of a prompt on an LLM.
- Flexible Job execution system (run more than just invoke_llm job).


## Getting Started

### Install

```bash
# Clone repository
git clone https://github.com/mzrinsky/ai-cli.git
cd ai-cli

# Install deps
uv sync
```


### Usage Examples

```bash
# an invocation passing only a system prompt and user prompt
> ./bin/ai-cli.py -s "Talk like a pirate"

# a simple invocation using a config file and a customized user prompt from the command line
> ./bin/ai-cli.py -c config.yaml -u "Give me a random interesting fact."

# Using a custom playbook (all CLI options override or extend config and playbook options where applicable)
> ./bin/ai-cli.py -c config.yaml -p custom-playbook.yaml -u "Give me a random interesting fact."

# Queue a job to be run by a worker
> ./bin/ai-cli.py -r seeder -j invoke_llm -p custom-playbook.yaml -u "Return an interesting fact about cats."

# Run a worker
> ./bin/ai-cli.py -r worker
```


### Config Example

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


### Playbook Example

```yaml
---
name: Invoke LLM Example Playbook
version: 1.0.0
schema_version: 1.0.0
model:
  provider: ollama
  init_args:
    model: qwen3:latest
    temperature: 0.8
    reasoning: True
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

More details of the design and implementation are located in [DESIGN.md](DESIGN.md)


## Disclaimer

This software is provided "as is" without warranty of any kind, either express or implied, including but not limited to the warranties of merchantability, fitness for a particular purpose and noninfringement. In no event shall the authors or copyright holders be liable for any claim, damages or other liability, whether in an action of contract, tort or otherwise, arising from, out of or in connection with the software or the use or other dealings in the software.
