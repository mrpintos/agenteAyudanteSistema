Purpose

This repository is a small LM Studio chat-agent prototype. The file `main.py` is the single entrypoint: it connects to a local LM Studio HTTP API, defines simple function-style tools, and runs an interactive REPL. These instructions tell an AI coding agent how to be immediately productive in this codebase.

Quick Start
- **Activate venv:** use the included virtual environment under `env/` or activate your own. Example:

```bash
source env/bin/activate
env/bin/python main.py
```

- **LM Studio:** ensure a local LM Studio server is running and serving models at `http://localhost:1234/v1` (default port 1234). The code uses a placeholder API key `lm-studio`.

Big-picture architecture
- **Single-file prototype:** `main.py` contains the whole flow: client config, tool registration, message loop, and response handling.
- **LM Studio via OpenAI-compatible client:** the code uses `openai.OpenAI` but points `base_url` at a local LM Studio server. The `model` field is present but LM Studio may ignore it.
- **Function-style tools:** tools are declared as JSON-serializable schemas (name, description, `parameters` JSON Schema) and passed to the chat completions call as `tools=`. Functions must be defined in Python and registered in the `tools` list.

Critical workflows & commands
- Run the app locally (REPL): `env/bin/python main.py`.
- If you edit dependencies, use the venv at `env/` or update a `requirements.txt` (none present).
- Debug common connectivity errors by confirming LM Studio is running, port `1234` is reachable, and the target model is loaded.

Project-specific conventions & patterns
- Language: the project uses Spanish in prompts and comments. Preserve Spanish system messages unless the user asks otherwise.
- System instruction: `main.py` sets a system-level message that disallows chain-of-thought reasoning ("No uses el razonamiento..."). AI agents editing prompts should respect and preserve this by default.
- Tools: follow the existing structure in `main.py` for registering tools. Each tool entry requires a valid JSON structure with `name`, `description`, and `parameters` (JSON Schema). Example pattern in `main.py`:

```py
tools = [
  {
    "type": "function",
    "name": "list_files_in_dir",
    "description": "Lista los archivos...",
    "parameters": { "type": "object", "properties": {"directory": {"type":"string"}}, "required": []}
  }
]
```

- Response extraction: the code expects `response.choices[0].message.content`. Maintain this access pattern when modifying response handling.

Integration points & external dependencies
- `openai` package configured to `base_url="http://localhost:1234/v1"` (LM Studio).
- `python-dotenv` is used to load environment variables (`load_dotenv()` in `main.py`). The active venv is included at `env/` in this workspace.

Common pitfalls to avoid
- Syntax & registration: when adding tools or functions, ensure the Python function exists and the `tools` list contains syntactically-correct JSON (commas, colons). The current `main.py` is a small prototype and contains some missing punctuation — preserve intent while fixing syntax.
- Do not change the default `base_url` unless adapting to a remote deployment; tests and local development expect LM Studio at `localhost:1234`.
- Preserve the system prompt and Spanish replies unless the maintainer explicitly asks for language changes.

When making changes
- Keep edits minimal and narrowly focused. This is a prototype — prefer small, reversible patches.
- If you add new function-tools, include a brief example usage in `main.py` and ensure the function's return is JSON-serializable.

Where to look
- Entrypoint and examples: `main.py` (client config, `tools` array, REPL loop)
- Virtual environment: `env/` (use `env/bin/python` to run locally)

If anything here is unclear or you want a different level of detail (for example, a ruleset for automated code generation vs. human edits), tell me which parts to expand and I will iterate.
