---
name: new-agent-network
description: Create a neuro-san agent network (HOCON under registries/), single-agent or multi-agent. Use when asked to create, add, or build an agent, agent network, or multi-agent system in this repo, or to change an existing network's agents.
---

# New agent network

Build the network, register it, then prove it answers. The network is done only when it is **green**: `ns validate`
passes and a one-shot chat returns an on-topic answer to every sample query.

## Steps

1. **Pin the design.** Name the network `<group>/<network_name>` (snake_case; group is a folder such as `basic`).
   Write down each agent: its name, the one job it does, and which agents or tools it calls. The first agent is the
   **Front Man**: the only agent that talks to the user. Done when every agent has one job and every down-chain call
   has an owner.

2. **Pick each tool's source**, first match wins:
   1. a toolbox tool: `{ "name": "...", "toolbox": "<tool>" }`. The list is in upstream
      [docs/toolbox.md](https://github.com/cognizant-ai-lab/neuro-san-studio/blob/main/docs/toolbox.md).
   2. an MCP server tool, configured in `mcp/mcp_info.hocon`. See the "MCP Servers" section of upstream
      [docs/user_guide.md](https://github.com/cognizant-ai-lab/neuro-san-studio/blob/main/docs/user_guide.md).
   3. a new coded tool: write the agent entry here, then follow the `new-coded-tool` skill for the Python.

3. **Write `registries/<group>/<network_name>.hocon`.** Copy the shape of `registries/basic/music_nerd.hocon`:
   - `metadata` with `description`, `tags`, and 2–3 `sample_queries`.
   - `include "registries/expertise_scoping_instructions.hocon"` and `include "config/llm_config.hocon"`.
   - Top-level `"max_steps"` and `"max_execution_seconds"`. Size them to the job (a small network: `100` and `300`).
   - `tools`: the Front Man first. Its `function` has a `description` and no `parameters`; it has no `class` and no
     `toolbox`.
   - In every agent, `function.description` says **what** it does (other agents read it to decide when to call it),
     and `instructions` say **how**. The agent's own `tools` list names only the agents and tools it calls.
   - A non-Front-Man agent takes inputs through `function.parameters` (an OpenAI function schema).
   - Secrets come from the environment: `${?MY_API_KEY}`.

   For a multi-agent network with routing between specialists, copy the AAOSA pattern from an upstream example such
   as [intranet_agents](https://github.com/cognizant-ai-lab/neuro-san-studio/blob/main/registries/industry/intranet_agents.hocon)
   (`include "registries/aaosa.hocon"` is already in this repo).

4. **Register it** in `registries/manifest.hocon`, beside the existing entries:
   - user-facing: `"<group>/<network_name>.hocon": true,`
   - support network called only by other networks: `"<group>/<network_name>.hocon": { "serve": true, "public": false },`

5. **Validate.** `.venv/bin/ns validate registries/<group>/<network_name>.hocon`. Fix and rerun until it prints
   `Validation passed`.

6. **Chat-test every sample query**, one at a time:

   ```bash
   echo "<sample query>" | PYTHONPATH=. .venv/bin/ns chat <group>/<network_name> --one-shot
   ```

   `PYTHONPATH=.` is required: without it, the `coded_tools` package that the pip wheel puts in site-packages
   shadows this repo's `coded_tools/`. A network with coded tools then fails with `Could not find class`.
   Done when each reply answers its query, and every down-chain agent or tool it should use was called. Agent
   traces are written to `/private/tmp/agent_thinking/`. A reply that is generic, or skips a tool it should have
   used, is **red**: fix the `function.description` or `instructions` and rerun.

7. **Report** the network name, its agents, and the chat replies, quoted.

## Reference

- Field reference for every HOCON key:
  [agent_hocon_reference.md](https://github.com/cognizant-ai-lab/neuro-san/blob/main/docs/agent_hocon_reference.md).
- Worked examples: upstream [docs/tutorial.md](https://github.com/cognizant-ai-lab/neuro-san-studio/blob/main/docs/tutorial.md)
  and [registries/](https://github.com/cognizant-ai-lab/neuro-san-studio/tree/main/registries). To copy one in:
  `.venv/bin/ns import <network>`.
- A per-agent model override goes in that agent's `llm_config`. The shared default is `config/llm_config.hocon`.
