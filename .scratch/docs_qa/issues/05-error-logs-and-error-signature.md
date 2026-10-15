# 05: Error logs and Error Signature

Spec: `docs/spec/docs_qa.md` (Error logs and secret redaction). ADR 0002.

**What to build:** a developer pastes a stack trace or compiler error and gets a likely root cause and fix steps.
Only a short Error Signature reaches the Specialists and MCP servers, never the log.

**Blocked by:** 04 (so the extractor never ships without redaction in front of it)

**Status:** completed

- [x] The `log_signature_extractor` coded tool turns an already-redacted log into an Error Signature: error type
      or code, message, library and version, and the top relevant frames.
- [x] The tool does no redaction. The regexes stay in the middleware (ADR 0002).
- [x] The Coordinator calls it before routing, and passes only the Error Signature to Specialists.
- [x] The library and version in the signature drive routing and the Relevant version.
- [x] Unit tests (pytest, deterministic) cover .NET exceptions, Java stack traces, Go panics, Node/npm errors and
      compiler errors.
- [x] An end-to-end fixture: a pasted log gets a reply naming a root cause and a fix, asserted with
      `keywords`/`gist`. This fixture is unverified, because the loop arrives in 06.
- [x] `ns validate` passes.

**Notes:**

- Tool: `coded_tools/docs_qa/assistant/log_signature_extractor.py`. Tests: `tests/unit/test_log_signature_extractor.py`
  (19 cases, including Go `[recovered]` panics and a Node.js error under `npm start`).
- Fixture: `tests/fixtures/docs_qa/assistant/error_log_root_cause_and_fix.hocon` (a Spring Boot log, routed to Context7).
  Passed on 2026-10-15 against the live LLM (2/3 samples, 32 s).
- Green: a one-shot run's agent trace shows the Coordinator calling the tool with the redacted log and passing only
  the Error Signature to the Context7 Specialist. No log lines reached the MCP calls. In the first run, the Coordinator
  added log details that were not in the signature (Spring Framework 6.1.6, the Hikari bean) to the Question. Step 2
  now forbids that, and a rerun confirmed it.
- `ns chat --one-shot` sends only the first line of stdin. To send a multi-line log, call neuro-san's `AgentCli` with
  `--one_shot --first_prompt_file <file>`.
- Compiler errors: C# (MSBuild) and TypeScript (tsc) are parsed. javac/Maven, `go build` and NuGet `NU` codes fall
  back to the first error line, with no library or version.
- A .NET exception in a `System.*` namespace takes its library from that namespace (for example `System`), not from the
  library in its frames.
