# 06: Verify-and-requery loop

Spec: `docs/spec/docs_qa.md` (The loop, Limits, User-facing reply shapes). ADR 0001.

**What to build:** every answer is checked before the user sees it. A rejected answer leads to a rewritten or split
Question, up to 3 Attempts. The user gets either a verified answer (with a footer counting the Excerpts it was
checked against) or the best attempt, marked unverified with the reason.

**Blocked by:** 02, 03

**Status:** completed (2026-10-16). Fixture tuning done after 07: see "Grounded tuning" in Notes.

- [x] The Coordinator calls the Verifier network through a same-server reference, passing `question` and
      `evidence_pack`.
- [x] The Verifier always judges against the original Question, or the standalone follow-up.
- [x] On INVALID, the internal Requerier receives the original Question, the failed Evidence Pack and the reason.
      It returns one or more Requeries, each with a suggested Specialist. It never answers.
- [x] Sub-questions from one Requerier output count as one Attempt.
- [x] The loop stops at VALID, after the 3rd Attempt, or on an Out-of-scope Question. The cap is enforced by the
      Coordinator's instructions.
- [x] The Unverified Answer is the attempt with the fewest failed Checks. A failed Grounded Check counts most, and
      a tie goes to the later attempt.
- [x] The reply shapes match the spec: the verified-answer footer, and the warning line for an Unverified Answer.
- [x] The limits match the spec's table. The Coordinator has `max_attempts = 1`, and the assistant network sets
      `request_timeout_seconds = 540` at the top level (raised from 360 with the maintainer, see Notes).
- [x] Passing end-to-end fixtures for:
  - a verified answer;
  - a Question that can't be grounded and ends as an Unverified Answer;
  - a Requery that recovers a wrong-version first answer.
- [x] Recorded observation from the test runs: did the Coordinator ever exceed 3 Attempts? If it did, raise the
      coded-counter fallback (ADR 0001) instead of building it here.
- [x] `ns validate` passes on both networks.

**Notes:**

- Coordinator tools: `Requerier` and `/docs_qa/verifier` (the LLM sees it as `__docs_qa__verifier`). Requerier:
  internal LLM agent, parameters `question`, `evidence_pack`, `reason`; returns `{"requeries": [{question,
  specialist}]}`, at most 2.
- Reply markers: a verified reply ends "Verified against N documentation Excerpts."; an Unverified Answer starts
  "Not verified: " plus the chosen Attempt's Verdict reason (the maintainer chose this over the last Verdict's
  reason; GLOSSARY.md updated).
- Limits changed with the maintainer after the first runs (spec Limits updated, with reasons):
  - Coordinator `max_steps` 60 → 240. It is LangGraph's recursion limit, and each of the 7 PII middleware entries
    adds a before_model and an after_model step to every LLM call, so a tool round costs about 16 steps. 60 ran
    out during Attempt 2.
  - Coordinator `max_execution_seconds` 300 → 480, `request_timeout_seconds` 360 → 540, Verifier 60 → 120. A merged
    pack of 3 Requery answers made the Verifier time out at 60 s twice, and a 3-Attempt run takes about 370 s.
  - Assistant fixtures: `timeout_in_seconds` 360 → 540.
- Added rules from the traces: the Coordinator calls the Verifier once per Attempt and a Specialist once per
  Question or Requery. A missing Verdict counts as INVALID with all three Checks failed; a missing pack counts as
  UNAVAILABLE. Before these rules, the Coordinator retried a timed-out Verifier and a timed-out Specialist on its own.
- Every assistant fixture now sets `"use_direct": true`. Without it the test driver looks for `/docs_qa/verifier`
  over HTTP, drops it as unreachable, and the Coordinator runs with no Verifier.
- Context7's anonymous monthly quota ran out on 2026-10-16. `mcp/mcp_info.hocon` now sends an optional key from
  `CONTEXT7_API_KEY` (keyless when unset; spec updated).
- Unit test: `tests/unit/test_assistant_limits.py` checks the Limits table and the Verifier reference.
- Observation, Attempt cap: in 6 traced runs and 9 fixture samples (2026-10-16), the Coordinator never started a 4th
  Attempt, so the coded counter (ADR 0001) is not needed yet. It did retry calls inside an Attempt (see above).
- Fixture results (2026-10-16, after the fixes above):
  - `requery_recovers_failed_first_answer`: passed (3 samples, 71 s).
  - `verified_answer_footer`: 1 of 3. One failing sample left out the `[n]` citation markers. The other failure
    was not reported (the driver reports only the first). A single sample passed earlier.
  - `unverified_ungroundable_question`: 1 of 3. One failing sample had a Specialist time out in Attempt 3, so it
    ended as an Unavailable Source reply, not an Unverified Answer (issue 07 owns that case).
- Wrong-version recovery was never seen: in the Vue 2.7, Tailwind 3.4, React Router 6.30 and Express 4.21 traces,
  the Context7 Specialist found the version-specific docs on Attempt 1. The Express fixture asserts the verified
  end state. In its trace, Attempt 1 failed Grounded and the Requery recovered.
  The fixture was renamed from `requery_recovers_wrong_version` to match what it checks (maintainer, 2026-10-16).
- Prompt tuning for the two 1-of-3 fixtures is deferred (maintainer, 2026-10-16). The unapproved additions found in
  review (one call per Specialist, the Requerier's "ask only about the subject" line, `p1-`/`p2-` ids, `use_direct`)
  are kept.
- Grounded tuning (2026-10-16, after 07):
  - The cause, from 5 INVALID Verdicts in the 07 manual-check traces:
    - All 5 failed Grounded, and the Verifier applied the spec correctly each time.
    - The Specialists' packs were wrong: `answer` had statements that no claim covered (caveats, asides such as
      "(StrictMode)", closing advice), and claims said more than their excerpts. The usual case was a parameter
      documented for one command, written as true for all the related commands.
    - The Requerier made it worse. Its rule "ask specifically for what that claim needed" turned off-topic
      statements (deployment slots, PowerShell) into Requeries, which widened the subject.
  - Changes, in `registries/docs_qa/assistant.hocon` only (the Verifier is unchanged):
    - Both Specialists write the pack in evidence order: `excerpts`, then `claims`, then `answer`, so the answer
      is built from the claims. This is the same idea as the Verifier's reason-before-verdict order.
    - New rules: a claim says only what its excerpts say and never generalizes to another command, API,
      setting or plan; `answer` is made only of the claims, with no extra caveat, tip or aside.
    - The Requerier asks for an unsupported statement only if the Question asks for it.
  - Results:
    - `verified_answer_footer` and `unverified_ungroundable_question` both passed (320 s together). The driver
      doesn't report per-sample counts for a pass, so it was at least 2 of 3 each.
    - `requery_recovers_failed_first_answer` passed (111 s).
    - A traced direct run of the 07 Cross-domain question (React fetch + Azure Functions CORS, both sources
      up) was VALID on Attempt 1 with 13 Excerpts. Before the change, the same question failed Grounded in all
      3 Attempts.
