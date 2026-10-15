# 04: Secret redaction on the Coordinator

Spec: `docs/spec/docs_qa.md` (Error logs and secret redaction). ADR 0002.

**What to build:** secrets pasted into a message are redacted before any LLM sees them: connection strings, bearer
tokens and JWTs, cloud keys, secret assignments, private keys, internal hostnames and private IPs, and emails.
Public cloud hostnames are kept.

**Blocked by:** 01

**Status:** completed

- [x] The Coordinator runs seven `PIIMiddleware` entries with `strategy: redact` and `apply_to_input: true`: the
      six custom `pii_type` names from the spec's table, each with a regex `detector`, plus the built-in `email`.
- [x] Only the generic internal-host suffixes are used. No organization suffixes.
- [x] Detector unit test (pytest, deterministic). It loads the detector regexes from the deployed assistant
      network HOCON (not a copy) and runs `PIIMiddleware` on sample logs. It asserts that:
  - every secret class is redacted;
  - public cloud hostnames such as `*.azurewebsites.net` and ordinary log text are unchanged.
- [x] Planted-secret end-to-end fixture. A log containing a fake connection string, token and key goes to the
      assistant network, and `not_keywords` asserts none of them appears in the reply. This proves the middleware is
      wired to the Coordinator.
- [x] `ns validate` passes.

**Notes:**

- The fixture is `tests/fixtures/docs_qa/assistant/planted_secret_error_log.hocon`. Passed on 2026-10-15 against the
  live LLM (one sample, both turns, 112 s).
- Known trade-offs, chosen to redact too much rather than too little:
  - Prose such as `The token: expired` or `password: must be ...` loses its value word.
  - The built-in `email` detector also takes `git@github.com` style user@host forms.
  - Bearer values under 20 characters, uppercase internal hostnames (`DB01.CORP`) and PGP key blocks are not
    redacted.
- Follow-up turns: neuro-san saves the user's raw message to chat history, and `PIIMiddleware` redacts only the
  newest user message. Fixed with `AllTurnsPIIMiddleware` (`middleware/docs_qa/`), a subclass with the same args that
  redacts every user message. Approved by the maintainer. ADR 0002 and the spec are updated.
