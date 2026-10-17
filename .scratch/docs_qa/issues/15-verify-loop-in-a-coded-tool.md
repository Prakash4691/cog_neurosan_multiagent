# 15: The verify loop runs in a coded tool

Spec: `docs/spec/docs_qa.md` (Networks and roles, The loop, Unavailable Source, Contracts, Limits, Testing Decisions).
ADR 0004.

**What to build:** move the fixed rules of the Coordinator's steps 4 to 7 out of its prompt and into an
`attempt_loop` coded tool. The Coordinator keeps the judgment calls and writes the reply.

**Blocked by:** None (can start immediately)

**Status:** ready-for-human (the LLM check needs Prakash's go-ahead on the Ollama Cloud quota)

**Why:** the Coordinator's prompt was about 2,700 tokens and went out with every Coordinator LLM call. About half
of it was fixed rules the model broke (issues 11, 12, 14). Every Evidence Pack also went through the Coordinator's
LLM, which wrote it out again for the Verifier and the Requerier. That slow output caused the timeouts in issue 14.

**Acceptance criteria:**

- [x] `coded_tools/docs_qa/assistant/attempt_loop.py` runs the loop: Specialist calls (concurrent within an
      Attempt), Unavailable Source handling, merge, mechanical pre-checks, Verifier, Requerier, the 3-Attempt cap,
      the choice of Unverified Answer, and URL numbering. It calls agents with `BranchActivation.use_tool()`.
- [x] The Coordinator calls `attempt_loop` once per Question and writes the reply from what it returns. Its
      instructions no longer hold steps 4 to 7's rules, and no longer include `expertise_scoping_instructions`,
      whose "Do not mention what you can NOT do" contradicted the decline and "Not answered" lines.
- [x] Specialists no longer write `source`, because `attempt_loop` sets it. The Requerier gets the failed pack
      without quotes.
- [x] Unit tests for the loop with scripted agent replies (`tests/unit/test_attempt_loop.py`).
- [x] ADR 0004, a pointer from ADR 0001, and the spec updated.
- [x] `ns validate` and the unit tests pass.
- [ ] Green run: the integration fixtures for `docs_qa/assistant` pass, and the nsflow UI shows a verified answer.
      All 15 assistant fixtures pass (2026-10-16). In the nsflow UI the graph shows `attempt_loop` connected to
      both Specialists, the Requerier and `/docs_qa/verifier`, and during a run its live view lights up
      Coordinator → attempt_loop → MicrosoftLearnSpecialist, then attempt_loop → /docs_qa/verifier (maintainer,
      2026-10-16).

**Notes:**

- The Coordinator's instructions went from about 2,700 to about 1,250 tokens (4 characters per token estimate). The
  Coordinator no longer sees the Excerpts' quotes, and its LLM no longer writes Evidence Packs out.
- Kept in the LLM on purpose: follow-up rewriting, routing and splitting Cross-domain Questions, the Out-of-scope
  decision, the Verifier's semantic checks (supports, version match, actionable), the Requerier's rewording, and the
  answer prose with the "Not verified" sentences. Version matching such as "7.9.4 matches 7.9" stays in the
  Verifier: version strings vary too much ("React Router v5", ".NET 8", "net8.0") for a reliable regex.
- Not moved: routing an Error Log by its signature's library. It is close to a lookup, but the Coordinator routes and
  splits the whole Question at once, and a code override would fight that.
- `use_tool()` is marked experimental in neuro-san, but the nsflow live view does show the sub-agent calls.
- `max_steps` 240 and the time limits are unchanged. Lower `max_steps` after a measured run.
- `ns validate` passed and unit tests passed (131, 2026-10-16).
- Fixture runs, 2026-10-16 (3 samples each, 2 must pass):
  - `verified_answer_footer` passed in 26 s.
  - `cross_domain_react_azure_functions` passed in 84 s.
  - `unverified_ungroundable_question` failed in 253 s. The reported sample was a verified answer, not
    "Not verified:". It says there is no "Flux Cache" client and gives the Azure.Core `ClientOptions.Retry`
    settings, with 11 Excerpts. Its version line named "Microsoft Learn:" twice, so it came from a merged pack of two
    Microsoft Learn Requeries: the Requerier widened the Question to Azure SDK retry options, and the Verifier passed
    the answer as RELEVANT although the product does not exist. No trace: pytest logs only warnings, and
    `logs/thinking_dir` is not written by fixture runs. The fixture passed before (issue 06), and was 1 of 3 once.
  - Fixed after that run: a merged pack from one source no longer repeats the source name in `version_covered`.
- Traced run of the same Question, 2026-10-16 20:50 (one sample, logging every call `attempt_loop` makes). It passed,
  but through the wrong path:
  - Attempt 1 (15 s): the Specialist said Microsoft Learn has no "Azure Quantum Flux Cache" client and returned no
    Excerpts. The precheck failed GROUNDED, so no Verifier call.
  - Requerier (17 s): one Requery that dropped "Flux Cache" and asked about the Azure.Quantum.Jobs client instead,
    which the failed pack's answer had named as what the documentation does cover.
  - Attempt 2: the Specialist timed out at 90 s on that wider Question, so the reply was the Attempt 1 Unverified
    Answer with the "became unavailable" note. It still contains "Not verified:", so the fixture passed.
  - The loop code behaved as specified. The cause of the 253 s failure is the Requerier swapping the product, which
    its rule "rephrase the Question in the terms the documentation is likely to use" allows. It is a prompt bug,
    not caused by the coded loop: the failed pack's own answer named the alternative product.
- Fix: the Requerier's Rules now say to keep every product, library, client and version name from the Question,
  even one the documentation does not mention, and never to swap in another product. Spec Requerier role updated.
  `ns validate` passed.
- Re-run after the Requerier fix, 2026-10-16: `unverified_ungroundable_question` passed in 192 s (at least 2 of 3;
  the driver does not report per-sample counts for a pass). All three fixtures picked for this issue now pass.
- More fixture runs, 2026-10-16:
  - `error_log_verified_root_cause_and_fix` passed in 71 s, `error_log_version_from_signature` in 101 s,
    `error_log_root_cause_and_fix` in 139 s, `planted_secret_error_log` in 114 s.
  - `requery_recovers_failed_first_answer` failed in 56 s on the keyword `next(` alone. The reported sample was a
    correct verified answer that passed errors with `.catch(next)`, so it never wrote `next(`. The keyword is now
    `next` (maintainer, 2026-10-16), and the re-run passed in 49 s. Its time suggests Attempt 1 was VALID, so the
    run did not show a requery; the fixture checks only the end state.
  - The remaining 7 passed: `context7_react_use_effect_cleanup` 80 s, `ms_learn_azure_managed_identity` 21 s,
    `context7_typescript_partial` 35 s, `ms_learn_github_actions_azure_deploy` 253 s,
    `context7_github_actions_branch_filter` 27 s, `out_of_scope_weather` 6 s,
    `follow_up_storage_account_powershell` 68 s.
