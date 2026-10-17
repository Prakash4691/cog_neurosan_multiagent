# cog-neurosan-multiagent

Multi-agent networks built with [neuro-san-studio](https://github.com/cognizant-ai-lab/neuro-san-studio).

The main network is **`docs_qa/assistant`**. It answers developer questions and explains pasted error logs, using only
current official documentation:

- Microsoft Learn, for Azure, .NET, Microsoft 365, Power Platform and other products documented there.
- Context7, for other libraries and frameworks (React, Go, Java, TypeScript and more).

Every answer is checked by a separate Verifier against the documentation excerpts found in the same run. If the
check fails, the question is rewritten and tried again, up to 3 times. An answer that is never verified is marked as
unverified. Secrets in pasted logs (connection strings, tokens, keys, internal hostnames) are redacted before any LLM
sees them.

The project also includes the scaffolded Agent Network Designer, for designing new networks in the nsflow UI.

## Requirements

- Python 3.13 and [uv](https://docs.astral.sh/uv/).
- [Ollama](https://ollama.com/), running locally and signed in to Ollama Cloud (`ollama signin`), with these models
  available:

  | Agent | Model |
  |---|---|
  | Coordinator (shared default, `config/llm_config.hocon`) | `kimi-k3:cloud` |
  | MicrosoftLearnSpecialist, Context7Specialist | `glm-5.3:cloud` |
  | Requerier | `glm-5.3-flash:cloud` |
  | Verifier | `deepseek-v4-pro:cloud` |

- Optional: `CONTEXT7_API_KEY` in `.env`, for Context7's higher rate limits.

## Setup

```bash
uv sync
source .venv/bin/activate
```

## Run

```bash
ns run                                               # Server and nsflow UI
PYTHONPATH=. ns chat docs_qa/assistant               # Terminal chat
echo "<question>" | PYTHONPATH=. ns chat docs_qa/assistant --one-shot
```

Set `PYTHONPATH=.` for `ns chat`. Without it, the `coded_tools` package installed with neuro-san-studio hides this
repo's `coded_tools/`, and local tools fail with `Could not find class`.

`--one-shot` sends only the first line of the input. For a multi-line error log, use the interactive chat or the UI.

## Observability

Traces go to a local [Phoenix](https://arize.com/docs/phoenix) server through the `PhoenixPlugin` in
`config/plugins.hocon`. Add this to `.env`:

```bash
PHOENIX_ENABLED=true
PHOENIX_AUTOSTART=true          # ns run starts Phoenix itself
PHOENIX_OTEL_REGISTER=false     # phoenix.otel.register() fails with the installed OTel exporter
OTEL_SERVICE_NAME=cog_neurosan_multiagent
```

Then run `ns run`, send a request, and open <http://localhost:6006>. Traces are in the `default` project. Each
request shows the agent calls, LLM calls (with prompts, replies and tokens), and MCP tool calls.

- Only the `ns run` server loads plugins. `ns chat` runs the network in its own process by default, so it is not
  traced. To trace a terminal chat, keep `ns run` running and add `--connection http --port 8080` to `ns chat`.
- Phoenix keeps traces in `~/.phoenix/phoenix.db`. They persist across restarts.
- On the first start, Phoenix creates its database. Do not stop it during that step, or the database is left half
  migrated. If Phoenix then fails with `table projects already exists`, delete `~/.phoenix` and start again.

## Test

```bash
pytest tests/unit                  # Fast, no LLM calls
pytest -m integration              # Runs the networks end to end against the live LLMs and MCP servers
ns validate registries/docs_qa/assistant.hocon
```

The integration tests use Ollama Cloud quota.

## Layout

| Path | Contents |
|---|---|
| `registries/` | Agent networks (HOCON). `manifest.hocon` lists the served networks. |
| `registries/docs_qa/` | `assistant.hocon` (Coordinator, Specialists, Requerier) and `verifier.hocon`. |
| `coded_tools/docs_qa/assistant/` | `attempt_loop.py` (the verify-and-retry loop) and `log_signature_extractor.py`. |
| `middleware/docs_qa/` | Secret redaction applied to every chat turn. |
| `config/` | Shared LLM config and plugins. |
| `mcp/mcp_info.hocon` | MCP server URLs, headers and tool allow lists. |
| `tests/` | Unit tests and integration fixtures. |

## Documentation

- [proj_architecure.md](proj_architecure.md): project architecture.
- [docs/spec/docs_qa.md](docs/spec/docs_qa.md): the `docs_qa` spec.
- [docs/adr/](docs/adr/): architecture decisions.
- [GLOSSARY.md](GLOSSARY.md): terms used across the code and docs.
