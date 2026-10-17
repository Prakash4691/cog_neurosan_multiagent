# AGENTS.md

This project builds multi-agent networks with [neuro-san-studio](https://github.com/cognizant-ai-lab/neuro-san-studio)
(installed from PyPI, see `pyproject.toml`). It was scaffolded with `ns init`.

## Reference: neuro-san-studio

Use the upstream repo as the source of truth for how to create agents. Read the relevant doc before you write a new
network, coded tool, or MCP/toolbox integration. Do not guess the HOCON schema.

| Topic | Upstream doc |
|---|---|
| Rules for coding agents | [AGENTS.md](https://github.com/cognizant-ai-lab/neuro-san-studio/blob/main/AGENTS.md) |
| Step-by-step tutorial (single agent, multi-agent, coded tools) | [docs/tutorial.md](https://github.com/cognizant-ai-lab/neuro-san-studio/blob/main/docs/tutorial.md) |
| HOCON, manifest, LLM config, coded tools, sly_data, toolbox, MCP, middleware, tests | [docs/user_guide.md](https://github.com/cognizant-ai-lab/neuro-san-studio/blob/main/docs/user_guide.md) |
| Full agent HOCON field reference | [neuro-san agent_hocon_reference.md](https://github.com/cognizant-ai-lab/neuro-san/blob/main/docs/agent_hocon_reference.md) |
| Prebuilt toolbox tools | [docs/toolbox.md](https://github.com/cognizant-ai-lab/neuro-san-studio/blob/main/docs/toolbox.md) |
| Example networks to copy from | [docs/examples.md](https://github.com/cognizant-ai-lab/neuro-san-studio/blob/main/docs/examples.md), [registries/](https://github.com/cognizant-ai-lab/neuro-san-studio/tree/main/registries), [coded_tools/](https://github.com/cognizant-ai-lab/neuro-san-studio/tree/main/coded_tools) |
| CLI (`ns`) | [docs/cli.md](https://github.com/cognizant-ai-lab/neuro-san-studio/blob/main/docs/cli.md) |

To read an upstream file from the terminal:

```bash
gh api repos/cognizant-ai-lab/neuro-san-studio/contents/docs/user_guide.md --header "Accept: application/vnd.github.raw"
```

To copy an upstream example network (and its coded tools) into this project: `ns import <group or network name>`.

## Project layout

- `registries/` — agent networks as HOCON files. `registries/manifest.hocon` lists which networks are served.
  - `basic/music_nerd.hocon` — the smallest working network. Start from it for a new single-agent network.
  - `agent_network_designer*.hocon`, `agent_network_editor.hocon`, etc. — the scaffolded designer family.
    It writes the networks it designs to `registries/generated/` and lists them in `registries/generated/manifest.hocon`.
  - `aaosa.hocon`, `expertise_scoping_instructions.hocon` — shared instruction blocks that networks `include`.
- `coded_tools/` — Python tools. A network `registries/<group>/<name>.hocon` resolves a short `class` such as
  `"order_lookup.OrderLookup"` to `coded_tools/<group>/<name>/order_lookup.py`.
- `middleware/` — `AgentMiddleware` classes used by the designer networks.
- `config/llm_config.hocon` — the one shared LLM config. Networks pull it in with `include "config/llm_config.hocon"`.
  It currently points at an Ollama Cloud model through the local Ollama daemon (`ollama signin` is required).
- `config/plugins.hocon` — observability and logging plugins.
- `mcp/mcp_info.hocon` — MCP server URLs, headers and tool allow lists.
- `logs/`, `nss_local.db` — runtime state. Git-ignored. Do not edit.

## Building agents

- New or changed agent network: use the `new-agent-network` skill.
- Custom Python tool for a network: use the `new-coded-tool` skill.
- Network rules to keep in mind even for small edits: the first agent in `tools` (the Front Man) is always an LLM
  agent; `function.description` says what an agent does and `instructions` say how; every network sets `max_steps`
  and `max_execution_seconds`; secrets come from the environment, never HOCON.
- The runtime name includes the subfolder: `registries/basic/foo.hocon` is addressed as `basic/foo`.
- Networks can also be designed interactively with the `agent_network_designer` network in the nsflow UI (`ns run`).

## Commands

Run from the repo root with the venv active (`source .venv/bin/activate`), or call `.venv/bin/ns`.

```bash
ns validate registries/<group>/<network_name>.hocon      # Check network structure (does not import coded tools)
ns check-config --hocon-path <file>.hocon               # Check LLM configs (default: config/llm_config.hocon)
echo "<query>" | PYTHONPATH=. ns chat <group>/<network_name> --one-shot   # One prompt, then exit
PYTHONPATH=. ns chat <group>/<network_name>              # Interactive terminal chat, no UI
ns chat --list                                           # List served agents
ns run                                                   # Start server + nsflow UI
ns import <network>                                      # Copy an upstream example into this project
ns export <group>/<network_name>                         # Bundle a network as .hocon or .zip
```

Set `PYTHONPATH=.` for `ns chat`. The pip wheel installs its own `coded_tools` package in site-packages, and without
the project root on `PYTHONPATH` that copy shadows this repo's `coded_tools/`: local tools fail with
`Could not find class`, and the designer networks run the wheel's copies instead of the local ones.

Dependencies are managed with `uv` (`uv add <package>`, `uv sync`). Python 3.13.
