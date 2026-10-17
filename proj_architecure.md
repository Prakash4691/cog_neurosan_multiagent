# Project architecture

This project is a [neuro-san-studio](https://github.com/cognizant-ai-lab/neuro-san-studio) project, scaffolded with
`ns init`. Almost everything is configuration: agent networks are HOCON files, and Python code goes only where an
agent needs logic. Most of the code is scaffolding from upstream. The project's own work is **`docs_qa`**, a grounded
documentation and error-log assistant.

## Layers

| Layer | Where | What it does |
|---|---|---|
| Agent networks | `registries/*.hocon` | Each file is one network: its agents, their instructions, tools and limits. `registries/manifest.hocon` decides which networks are served and whether they are public. |
| Coded tools | `coded_tools/<group>/<network>/` | Python `CodedTool` classes that a network calls. They are matched to a network by folder path. |
| Middleware | `middleware/` | `AgentMiddleware` classes that run around an agent's LLM calls (redaction, validation, saving files). |
| Shared config | `config/llm_config.hocon`, `mcp/mcp_info.hocon` | One LLM for all networks (`glm-5.3:cloud` through the local Ollama daemon) and the MCP server URLs with their tool allow lists. |
| Runtime | `ns run` / `ns chat` | The neuro-san server and the nsflow UI from the PyPI wheel. `main.py` is an unused stub. |

## Served networks (`registries/manifest.hocon`)

- **`docs_qa/assistant`** (public) and **`docs_qa/verifier`** (served, not public): the project's own work. See the
  next section.
- **Agent Network Designer family** (`agent_network_designer`, `agent_network_editor`,
  `agent_network_instructions_editor`, `agent_network_query_generator`, `tools/internet_info_gatherer`,
  `agent_network_test_generator`): upstream scaffolding. It designs new networks and writes them to
  `registries/generated/`. Its tools are in `coded_tools/agent_network_editor/`. Its middleware is in
  `middleware/agent_network_designer/`, split into `validation/` (checks structure and instructions) and
  `persistence/` (puts the network together and writes HOCON).
- **`basic/music_nerd`**: the smallest example network.
- **`experimental/cruse_theme_agent`, `experimental/cruse_widget_agent`**: support networks for the CRUSE adaptive UI.

## docs_qa

```
User ──► [AllTurnsPIIMiddleware ×7]  redacts secrets in every turn before any LLM sees them (ADR 0002)
            │
            ▼
       Coordinator (Front Man, LLM)
         ├─ log_signature_extractor  (coded tool: redacted log → short Error Signature)
         └─ attempt_loop             (coded tool: the whole verify loop, ADR 0004)
               │  use_tool(), up to 3 Attempts, 360 s budget
               ├─► MicrosoftLearnSpecialist ──► Microsoft Learn MCP
               ├─► Context7Specialist       ──► Context7 MCP
               ├─► /docs_qa/verifier        (separate network, ADR 0003)
               └─► Requerier                (rewrites or splits the Question after a failed Attempt)
```

Files:

- `registries/docs_qa/assistant.hocon`: Coordinator, the two Specialists, Requerier and the two coded tools.
- `registries/docs_qa/verifier.hocon`: the Verifier network.
- `coded_tools/docs_qa/assistant/attempt_loop.py`: the verify-and-requery loop.
- `coded_tools/docs_qa/assistant/log_signature_extractor.py`: Error Signature extraction.
- `middleware/docs_qa/all_turns_pii_middleware.py`: secret redaction across all turns.

### Request flow

1. **Redaction first.** `AllTurnsPIIMiddleware` is a small subclass of LangChain `PIIMiddleware`. It redacts every
   turn, not only the newest, because neuro-san sends the raw history again on each turn. There are seven entries,
   one per secret type (connection strings, tokens, keys and so on). It runs before the Coordinator's LLM because
   every LLM here is a cloud model.
2. **The Coordinator makes the judgment calls.** It writes the standalone Question (this handles follow-ups),
   extracts the Error Signature, chooses the Specialist(s) and splits the Question into parts, or declines if the
   Question is out of scope. At the end it writes the reply.
3. **`attempt_loop` does the fixed steps:**
   - It asks the Specialists in parallel and merges their Evidence Packs.
   - `precheck` runs cheap checks in code first: no excerpts, a claim that cites nothing, no version. A pack that
     fails one is INVALID without a Verifier call.
   - Otherwise the Verifier judges the pack as GROUNDED, RELEVANT and ACTIONABLE.
   - If the pack is INVALID, the Requerier writes new queries for the next Attempt.
   - The loop stops on VALID, after 3 Attempts, when time runs out, or when a source goes down partway through. If
     no Attempt passed, it returns the best one, marked as unverified.
   - It returns the parts of the reply that need no LLM: claims, source numbers, version, Sources list and footer.
     The Evidence Packs never pass through the Coordinator's LLM.
4. **The Verifier is its own network.** neuro-san test fixtures can only talk to a network's Front Man, so a separate
   network can be tested alone against a golden set. It declares `question` and `evidence_pack` as explicit
   parameters, so they are not merged into one string.

`log_signature_extractor` turns redacted logs into Error Signatures. It handles .NET, Java and Python-style
exceptions, Go panics, compiler errors, npm errors and JSON error bodies, and has a fallback for anything else.

### Why a hub, and why in code

- **ADR 0001** rejected a chain of agents (Coordinator → Verifier → Requerier → back). neuro-san runs a cycle as
  nested calls, so no agent would know the Attempt count. One hub owns the original Question and the count.
- **ADR 0004** moved the hub from the Coordinator's prompt into code. The model broke the prose rules, and copying
  Evidence Packs through the LLM caused timeouts.

### Limits

| Agent | `max_steps` | `max_execution_seconds` |
|---|---|---|
| docs_qa/assistant (network) | 240 | 480 |
| attempt_loop (own budget) | — | 360 |
| Specialists, Requerier | 20 / 10 | 120 |
| docs_qa/verifier (network) | 10 | 120 |

The loop's 360 s budget leaves the Coordinator time for its final reply.

## Tests

- `tests/unit/`: tests for the coded tools and middleware that need no LLM: attempt loop, signature extractor, secret
  redaction, limits, golden-set format, Context7 URL.
- `tests/integration/test_network_fixtures.py`: runs the HOCON fixtures in `tests/fixtures/docs_qa/` against the
  real networks with `DynamicHoconUnitTests`. These call the LLM.

## Design records

- `docs/spec/docs_qa.md`: the spec.
- `docs/adr/0001`–`0004`: architecture decisions.
  - 0001: the Coordinator owns the verify-and-requery loop (hub, not a cycle).
  - 0002: secrets are redacted by middleware before any LLM.
  - 0003: the Verifier is a separate network.
  - 0004: the verify loop runs in a coded tool.
- `GLOSSARY.md`: terms such as Attempt, Evidence Pack, Error Signature and Unverified Answer.
- `.scratch/docs_qa/issues/`: local issue tracker.
