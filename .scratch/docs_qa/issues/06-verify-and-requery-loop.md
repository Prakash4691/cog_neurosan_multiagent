# 06: Verify-and-requery loop

Spec: `docs/spec/docs_qa.md` (The loop, Limits, User-facing reply shapes). ADR 0001.

**What to build:** every answer is checked before the user sees it. A rejected answer leads to a rewritten or split
Question, up to 3 Attempts. The user gets either a verified answer (with a footer counting the Excerpts it was
checked against) or the best attempt, marked unverified with the reason.

**Blocked by:** 02, 03

**Status:** ready-for-agent

- [ ] The Coordinator calls the Verifier network through a same-server reference, passing `question` and
      `evidence_pack`.
- [ ] The Verifier always judges against the original Question, or the standalone follow-up.
- [ ] On INVALID, the internal Requerier receives the original Question, the failed Evidence Pack and the reason.
      It returns one or more Requeries, each with a suggested Specialist. It never answers.
- [ ] Sub-questions from one Requerier output count as one Attempt.
- [ ] The loop stops at VALID, after the 3rd Attempt, or on an Out-of-scope Question. The cap is enforced by the
      Coordinator's instructions.
- [ ] The Unverified Answer is the attempt with the fewest failed Checks. A failed Grounded Check counts most, and
      a tie goes to the later attempt.
- [ ] The reply shapes match the spec: the verified-answer footer, and the warning line for an Unverified Answer.
- [ ] The limits match the spec's table. The Coordinator has `max_attempts = 1`, and the assistant network sets
      `request_timeout_seconds = 360` at the top level.
- [ ] Passing end-to-end fixtures for:
  - a verified answer;
  - a Question that can't be grounded and ends as an Unverified Answer;
  - a Requery that recovers a wrong-version first answer.
- [ ] Recorded observation from the test runs: did the Coordinator ever exceed 3 Attempts? If it did, raise the
      coded-counter fallback (ADR 0001) instead of building it here.
- [ ] `ns validate` passes on both networks.
