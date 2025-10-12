# ai-cli.py Design

> An attempt to document some of the design choices.

Some of the goals for this project.

 - Queue the execution of a job.
 - Run other jobs in the future (not just LLM) 
 - Make writing new jobs easy.
 - Make running prompts really easy / chainable with normal pipes & redirects
 - Make it easy to add new tools to the LLM
 - Run without a RabbitMQ server (local-only with no extra setup)
 - Support multiple backends (not just Ollama)
 - Run multiple workers (distributed task queue)
 - Log / monitor / respond to results from jobs.


## Basic Terminology

In an attempt at code-reuse the following roles were identified to encapsulate components with overlapping behavior.

 - `Consumer`: Consume jobs or results
 - `Seeder`: Seed (publish) items into a queue.
 - `Logger`: Log or introspect queue items (without consuming them).
 - `Hybrid`: A mix of the above roles in a single client.

In addition to these roles some other core components have been defined.

- `Job`: A task that can be invoked with ai-cli.
- `Playbook`: A declarative yaml file containing configuration data for a job invocation.
- `Config`: A yaml config file containing application level configuration data.
- `Queue`: A message broker queue.


## Overview

### Jobs

In this initial release there are only 2 jobs included by default.

 - `echo`: A job which returns any input data back as a result.  Can be used for testing and is an example of a simple job.
 - `invoke_llm`: A job which runs a prompt on a local LLM (currently though Ollama) using LangChain & LangGraph with support for tool-calling and MCP servers.


#### Features of invoke_llm

 - Built on top of LangChain and LangGraph to allow easy integration of new tools.
 - Dynamically loads the `tools/` directory on invocation, allowing on-the-fly new tools (each time invoke_llm is run).
 - Uses a factory pattern to load the ChatModel, which allows the user to easily add new LangChain backends (e.g. HuggingFace, OpenAI, ChatGPT).
 - Supports MCP servers for even more tools
   - Add any existing mcp server to the config to make it available to the LLM.
   - Can use MCP servers from [https://github.com/mcp](https://github.com/mcp) via. simple config.
 - The LLM has the ability to run tools multiple times to accomplish it's goal.


### Config Files

These hold application level configuration information, and are used to control how ai-cli.py behaves.


### Playbook Files

These hold job level configuration information and are used to control how a job behaves.


## Internals

Browse the source for now, generated documentation is on the [ROADMAP.md](ROADMAP.md).

