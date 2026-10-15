# Secrets are redacted by middleware before any LLM; the coded tool only extracts the Error Signature

Error Logs often contain secrets (connection strings, tokens, keys, internal hostnames). Every agent's LLM, including
the Coordinator's, is a cloud model (Ollama Cloud), so redacting inside a coded tool would be too late: the
Coordinator's LLM would already have seen the raw log and would have to copy it into the tool call. Instead, the
Coordinator runs LangChain `PIIMiddleware` entries, one custom `pii_type` with a regex `detector` per secret class,
with `strategy: redact` and `apply_to_input: true`. These redact the user's message before the first LLM call. The
`log_signature_extractor` coded tool then only turns the redacted log into an Error Signature, and only the
signature goes to Specialists and MCP servers.

## Considered Options

- Redact inside `log_signature_extractor`: rejected, because the raw log reaches the Coordinator's cloud LLM first.
- A custom middleware class that redacts and replaces the log with its signature: the most private option, but it
  is a new class to maintain and hides the full log from the Coordinator. Revisit if copying the redacted log into
  the tool call turns out to be lossy.

## Consequences

- Do not move the redaction regexes into the coded tool. That would bring the cloud-LLM leak back.
- Checked on langchain 1.4.5: custom `pii_type` names with a string `detector` redact the message in place
  (for example `[REDACTED_CONNECTION_STRING]`).
