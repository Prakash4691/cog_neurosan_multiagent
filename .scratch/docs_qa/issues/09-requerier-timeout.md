# 09: Requerier timeout cuts the loop short

Spec: `docs/spec/docs_qa.md` (The loop, Limits).

**What to build:** the Requerier gets enough time to answer on long inputs, and the spec says what the Coordinator
does when the Requerier still fails.

**Blocked by:** None (can start immediately)

**Status:** completed (2026-10-16)

**Found in:** manual testing in the nsflow UI, 2026-10-16. Traces: `logs/thinking_dir/Coordinator.Requerier`,
`logs/thinking_dir/Coordinator.Requerier-02`.

**What happened:**

- The Requerier timed out in 2 of its 3 calls: `Agent timed out: max_execution_seconds=60s exceeded.`
  - 12:56:56, the PCF question ("how can I check this is dataverse pcf component"), after Attempt 1.
  - 13:16:54, the Dataverse `0x80048d19` Error Log, after Attempt 2.
- Its one successful call (13:15:47) took 17 s.
- The Requerier is one LLM call with no tools. Its input is the Question, the full failed Evidence Pack and the
  Verdict reason. On a large pack, the cloud model takes more than 60 s.
- After each timeout the Coordinator stopped and returned an Unverified Answer, so the PCF run never got an
  Attempt 2 and the Error Log run never got an Attempt 3.
- The spec's loop has no rule for a Requerier failure. The Coordinator's "stop and return the best attempt" is
  reasonable, but it is not written down.

**Acceptance criteria:**

- [x] Raise the Requerier's `max_execution_seconds` in `registries/docs_qa/assistant.hocon`. 120 s matches the
      Verifier, which also reads a full Evidence Pack. Check that the Coordinator's 480 s and the
      `request_timeout_seconds` of 540 still cover a 3-Attempt run with the new value, and change them if not.
- [x] Update the spec's Limits table and `tests/unit/test_assistant_limits.py` to match.
- [x] The spec's loop section says what happens when the Requerier returns no Requeries (a timeout, an error or
      an empty list): the loop ends and the user gets the Unverified Answer from the best attempt so far. The
      Coordinator's instructions say the same.
- [x] `ns validate` and the unit tests pass.
- [x] Re-run the PCF question once in the UI and record whether the Requerier now returns Requeries. One run only:
      see the Ollama Cloud quota note.

**Notes:**

- Requerier `max_execution_seconds` 60 -> 120 in `registries/docs_qa/assistant.hocon`. The spec Limits table and
  `tests/unit/test_assistant_limits.py` match.
- Coordinator 480 s and `request_timeout_seconds` 540 are unchanged. A typical 3-Attempt run is about 370 s and
  includes two fast Requerier calls. A run where both Requerier calls take close to 120 s can still reach 480 s.
  The spec's Limits notes say this.
- Requerier failure rule: Coordinator step 4g now says that no Requeries (an error, a timeout or an empty list)
  ends the loop with the Unverified Answer from the Attempts so far. The spec's loop section lists it as an end
  condition.
- `ns validate` and unit tests passed (110, 2026-10-16). No LLM run yet: the manual re-run is for Prakash.
- Manual re-run, 2026-10-16 13:47 (nsflow UI, "how can I check this is in dataverse pcf component", a follow-up
  to the React question):
  - The Requerier returned Requeries in 80 s, 31 s and 65 s. The first call would have timed out at 60 s.
  - The loop reached Attempt 3. Then the Coordinator hit its 480 s limit during Attempt 3's Verifier call, and the
    user got no reply. This is the risk named above. New ticket: see "Follow-up".
  - After Attempt 1 the Coordinator called the Requerier twice: the second call passed one Requery as
    `evidence_pack`. It cost 31 s.

**Follow-up:** the time budget on the cloud model (a Specialist timeout, the Coordinator's 480 s, the double
Requerier call): issue 14.
