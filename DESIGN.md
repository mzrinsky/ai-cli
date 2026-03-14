# ai-cli.py Design

> Document the design choices and architecture of the project.


Some of the goals for this project. (`ai-cli.py` already does some of these things.)

 - Queue the execution of `Jobs`
 - Enable running multiple workers (distributed task queue)
 - Provide other useful jobs in the future (not just LLM)
 - Make writing new jobs easy
 - Add Image I/O support (vision models)
 - Make running prompts really easy / chainable with normal pipes & redirects
 - Make it easy to add new tools to the LLM
 - Run without a RabbitMQ server (local-only with no extra setup)
 - Support multiple backends / frameworks (Semantic Kernel, LM Studio, etc.)
 - Support popular Services (OpenAI, Anthropic, etc.)
 - Log / monitor / respond to results from `Jobs`
 - Provide a TUI / GUI for interacting with `Consumers` / `Jobs` / `Results` etc.


## Overview

 - `Config`: Holds application level configuration information, and is used to control how ai-cli.py behaves.
 - `Playbook`: Holds `Job` level configuration information and is used to control how a job behaves.
 - `Job`: This is the code run with the `Playbook` information.


## Basic Terminology

The following roles encapsulate the various behaviors of the system.

 - `Consumer`: Consume jobs or results
 - `Seeder`: Seed (publish) items into a queue.
 - `Logger`: Log or introspect queue items (without consuming them).
 - `Hybrid`: A mix of the above roles in a single client.

In addition to these roles some other core components have been defined.

- `Job`: A task that can be invoked with ai-cli.
- `Playbook`: A declarative yaml file containing configuration data for a job invocation.
- `Config`: A yaml config file containing application level configuration data.
- `Queue`: A message broker queue.


## Jobs

In this initial release there are only 2 jobs included by default.

 - `echo`: A job which returns any input data back as a result.  Can be used for testing and is an example of a simple job.
 - `invoke_llm`: A job which runs a prompt on a local LLM (currently though Ollama) using LangChain & LangGraph with support for tool-calling and MCP servers.


#### Features of invoke_llm Job

 - Built on top of LangChain and LangGraph to allow easy integration of new tools.
 - Dynamically loads the `tools/` directory on invocation, allowing on-the-fly new tools (each time invoke_llm is run).
 - Uses a factory pattern to load the ChatModel, which allows the user to easily add new LangChain backends (e.g. HuggingFace, OpenAI, ChatGPT).
 - Supports MCP servers for even more tools
   - Add any existing mcp server to the config to make it available to the LLM.
   - Can use MCP servers from [https://github.com/mcp](https://github.com/mcp) via. simple config.
 - The LLM has the ability to run tools multiple times to accomplish it's goal.


## Internals

Good places to start:
 - [jobs/invoke_llm.py](jobs/invoke_llm.py) : The `invoke_llm` Job.
 - [src/ai_cli/job_queue.py](src/ai_cli/job_queue.py) : The main `Interface` and `Class` implementations.

For more, browse the source, generated API documentation is on the [ROADMAP.md](ROADMAP.md).
