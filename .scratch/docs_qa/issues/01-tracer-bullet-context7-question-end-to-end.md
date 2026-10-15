# 01: Tracer bullet: Context7 question end to end

Spec: `docs/spec/docs_qa.md`. Vocabulary: `GLOSSARY.md`.

**What to build:** a developer asks a library question (for example about a React hook) in the `docs_qa/assistant`
network and gets an answer taken from Context7, with numbered source links. The network has only the Coordinator
and the Context7 Specialist. There is no verification yet. This ticket also sets up the test tooling every later
ticket uses.

**Blocked by:** None (can start immediately)

**Status:** ready-for-agent

- [ ] `pytest` is added as a dev-only dependency. No runtime dependencies are added.
- [ ] Both MCP servers are registered keyless in the MCP server config, each with a tool allow list:
      Microsoft Learn (docs search, code-sample search, docs fetch) and Context7 (resolve library ID, query docs).
- [ ] The Context7 Specialist's server URL is a network-level HOCON value. It matches the URL key in the MCP server
      config exactly, so the allow list applies.
- [ ] The Context7 Specialist resolves the library ID, then queries the docs, and returns an Evidence Pack in the
      spec's shape: source, status, version covered, answer, claims with Excerpt ids, and verbatim Excerpts.
- [ ] The Specialist never answers from model memory.
- [ ] The Coordinator shows the user the answer and numbered source links, not the Excerpts.
- [ ] The network has `max_steps` and `max_execution_seconds` set, using the spec's limits for these two agents.
- [ ] The network is registered in the manifest, and `ns validate` passes.
- [ ] An end-to-end data-driven fixture (a React question) passes, asserting with `keywords`/`gist` and a
      `success_ratio`, with `timeout_in_seconds = 360`.
