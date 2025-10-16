# ai-cli.py Roadmap

A current roadmap of planned features for ai-cli.py

## Planned Features

For now this is simply a list of all ideas and features.

They are not in order of priority and no time-frame planned for release.

If a feature is important to you, consider supporting this project financially.

- Make use of the available middleware https://docs.langchain.com/oss/python/langchain/middleware
- Make full use of create_agent from LangChain as it overlaps so much with our goals in invoke_llm.
- ~~Read from a default config file someplace.~~ Will now check for ~/.config/ai-cli/default.yaml
- Add additional chat models to the chat model factory (e.g. HuggingFace etc.)
- Add additional jobs for things like image generation, image classification etc.
- Add the ability for invoke_llm to queue tasks back into ai-cli (custom tool)
- Add context support for invoke_llm to allow inclusion of content from various sources (and a docs section to the playbooks).
- Add support for rules section of playbooks (to include additional custom instructions for the LLM)
- Expand the local tools available for invoke_llm.
- Add support for saving / loading a chat history with invoke_llm to allow the user to continue a conversation.
- Add support for opening a side-channel websocket from a worker to allow streaming a response to a client
- Expand support for dealing with and returning various data formats (images etc.)
- Add support for piped inputs on the command line (to allow chaining and piping images as input etc.)
- Add support for tracking multiple jobs across a single request.
- Add an interactive mode with a useful TUI providing a slick interface into queues, jobs, responses, results etc.
- Expand unit testing and coverage
- Ensure deadletter routing and logic is sound and enabled by default to prevent loops or stuck jobs etc.
- Expand documentation and examples / resources
- Generate code documentation
- Improve the RabbitMQ client implementation to be well-behaved (heartbeat support, re-connection logic etc.)
- Ensure the RabbitMQ client supports complex network configs (for multiple servers, fallbacks etc)
- Improve message routing support for complex use cases (e.g. send results to specific hosts, etc.)
- Make all role use-cases work (e.g. logger) which will require additional queue routing and queues along with some sort of configuration to allow control of which messages to log and inspect.
- Support alternate front-ends and integrations. (more than just cli etc.)
- Investigate exposing functionality as MCP server or APIs for other tools / integrations.
- Investigate ingesting API services from other AI service providers.
