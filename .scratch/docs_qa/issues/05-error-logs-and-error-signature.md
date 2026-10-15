# 05: Error logs and Error Signature

Spec: `docs/spec/docs_qa.md` (Error logs and secret redaction). ADR 0002.

**What to build:** a developer pastes a stack trace or compiler error and gets a likely root cause and fix steps.
Only a short Error Signature reaches the Specialists and MCP servers, never the log.

**Blocked by:** 04 (so the extractor never ships without redaction in front of it)

**Status:** ready-for-agent

- [ ] The `log_signature_extractor` coded tool turns an already-redacted log into an Error Signature: error type
      or code, message, library and version, and the top relevant frames.
- [ ] The tool does no redaction. The regexes stay in the middleware (ADR 0002).
- [ ] The Coordinator calls it before routing, and passes only the Error Signature to Specialists.
- [ ] The library and version in the signature drive routing and the Relevant version.
- [ ] Unit tests (pytest, deterministic) cover .NET exceptions, Java stack traces, Go panics, Node/npm errors and
      compiler errors.
- [ ] An end-to-end fixture: a pasted log gets a reply naming a root cause and a fix, asserted with
      `keywords`/`gist`. This fixture is unverified, because the loop arrives in 06.
- [ ] `ns validate` passes.
