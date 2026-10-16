# 08: Verified error-log answer end to end

Spec: `docs/spec/docs_qa.md` (Checks: Actionable).

**What to build:** a pasted error log now goes through the full loop. The developer gets a verified root cause and
fix tied to the Error Signature, or an Unverified Answer that says why.

**Blocked by:** 05, 06

**Status:** completed (2026-10-16)

- [x] An end-to-end fixture: a pasted log with a known, documented fix ends in a verified reply that names the root
      cause and the fix, with the verified-answer footer.
- [x] The Relevant Check uses the library and version from the Error Signature even when the user stated no
      version. An end-to-end fixture shows this with a log naming a specific library version.
- [x] The planted-secret fixture from 04 still passes with the loop in place.

**Notes:**

- Verified root cause and fix: `tests/fixtures/docs_qa/assistant/error_log_verified_root_cause_and_fix.hocon`.
  - The log is a Blazor Web App `InvalidOperationException` for a service that is registered only in the `.Client`
    project. It routes to Microsoft Learn.
  - The Learn page "Client-side services that fail during prerendering" quotes this error and both fixes (checked
    with a direct `microsoft_docs_search` call, no LLM).
  - The fixture asserts "Root cause:", "Fix:", "prerender", the sources and "Verified against", and asserts that
    "Not verified" is absent. The full footer shape is `verified_answer_footer`'s job.
  - Passed on 2026-10-16 (3 samples, 163 s).
- Version from the Error Signature: `tests/fixtures/docs_qa/assistant/error_log_version_from_signature.hocon`.
  - The user names no version. The log's jars give the signature `spring-boot-autoconfigure` 3.4.1.
  - The reply must be verified and contain "3.4" and "spring.datasource.url". The user never wrote "3.4": it came
    from the log, through the signature.
  - This shows the end state only. The Coordinator also writes the signature's library and version into the
    Question (step 2), so the fixture can't tell whether the Verifier read the version from the signature or from
    the Question text. Showing that needs a Verifier golden-set case (see Follow-up).
  - Passed on 2026-10-16 (3 samples, 282 s).
- Why a new Spring Boot log, not the 05 fixture's log: Context7's Spring Boot versions (checked 2026-10-16) are
  2.2.8, 2.5.5, 2.7.18, 3.1.12, 3.3.11, 3.4.1, 3.5.3, 3.5.9 and 4.x. There is no 3.2.x, so the 05 log (3.2.5) can't
  pass the Relevant Check and can't end verified. The 05 fixture is unchanged. Its comment now says this.
- Verifier wording (`registries/docs_qa/verifier.hocon`):
  - Relevant and Actionable said "if the Question **is** an Error Signature", and the `question` parameter
    description said the same.
  - The Coordinator sends the user's request followed by "Error Signature: {...}". So the wording now says
    "contains an Error Signature".
  - Relevant now reads "the exact product, framework and version that the Question or its Error Signature
    names", the spec's wording. The signature's library and version count even when the user names no version.
  - The golden set passed after the change (all 7 fixtures, 106 s, 2026-10-16).
- Planted secret: `planted_secret_error_log` passed with the loop in place (1 sample, both turns, 89 s, 2026-10-16).
- The driver doesn't report per-sample counts for a pass, so each 2/3 fixture passed at least 2 of 3.

**Follow-up (for the maintainer):**

- A golden-set case that isolates the Relevant rule for an Error Signature. The `question` holds a request with
  no version plus an Error Signature with a version (say Spring Boot 3.4.1). The pack covers another version (say
  3.5.x). Expected: INVALID, with RELEVANT failed. The spec leaves the golden set's contents to the maintainer.
