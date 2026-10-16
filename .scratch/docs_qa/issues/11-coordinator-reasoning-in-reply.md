# 11: Coordinator puts its own reasoning in the reply

Spec: `docs/spec/docs_qa.md` (User-facing reply shapes).

**What to build:** the user's reply holds only the reply shape from the spec. The Coordinator's notes to itself
never reach the user.

**Blocked by:** None (can start immediately)

**Status:** completed (2026-10-16)

**Found in:** manual testing in the nsflow UI, 2026-10-16. Trace: `logs/thinking_dir/Coordinator`, the reply at
12:58:13.

**What happened:**

- After the Requerier timed out (see 09), the reply to "how can I check this is dataverse pcf component" started
  with:

  > The Requerier did not return Requeries (it timed out), so there is nothing to start Attempt 2 with. I'll stop
  > and give the Unverified Answer from Attempt 1.

- Then came the "Not verified:" line and the answer. The Unverified Answer shape is a warning line at the top, then
  the answer. Internal terms (Requerier, Requeries, Attempt) are not for the user.
- The Coordinator narrates before most tool calls ("I'll get Requeries for the next attempt."). Those messages
  stay internal. This one was written in the same message as the final reply, so it went to the user.

**Acceptance criteria:**

- [x] The Coordinator's instructions say the final reply starts with the reply shape itself (the answer, the
      "Not verified:" warning, the decline or the unavailable-source note) and contains no notes about the loop,
      agents or Attempts.
- [x] `ns validate` passes.

This is an instruction change only. No new fixture.

**Notes:**

- Coordinator step 7 now says the reply starts with its first line and says nothing about the steps: no Attempts,
  Specialists, Requerier, Requeries, Verifier or Verdicts.
- `ns validate` passed. Not checked with an LLM run yet.
