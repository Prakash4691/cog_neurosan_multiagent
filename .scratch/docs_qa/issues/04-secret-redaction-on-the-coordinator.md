# 04: Secret redaction on the Coordinator

Spec: `docs/spec/docs_qa.md` (Error logs and secret redaction). ADR 0002.

**What to build:** secrets pasted into a message are redacted before any LLM sees them: connection strings, bearer
tokens and JWTs, cloud keys, secret assignments, private keys, internal hostnames and private IPs, and emails.
Public cloud hostnames are kept.

**Blocked by:** 01

**Status:** ready-for-agent

- [ ] The Coordinator runs seven `PIIMiddleware` entries with `strategy: redact` and `apply_to_input: true`: the
      six custom `pii_type` names from the spec's table, each with a regex `detector`, plus the built-in `email`.
- [ ] Only the generic internal-host suffixes are used. No organization suffixes.
- [ ] Detector unit test (pytest, deterministic). It loads the detector regexes from the deployed assistant
      network HOCON (not a copy) and runs `PIIMiddleware` on sample logs. It asserts that:
  - every secret class is redacted;
  - public cloud hostnames such as `*.azurewebsites.net` and ordinary log text are unchanged.
- [ ] Planted-secret end-to-end fixture. A log containing a fake connection string, token and key goes to the
      assistant network, and `not_keywords` asserts none of them appears in the reply. This proves the middleware is
      wired to the Coordinator.
- [ ] `ns validate` passes.
