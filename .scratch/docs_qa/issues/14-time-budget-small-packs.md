# 14: Runs time out because Evidence Packs are large

Spec: `docs/spec/docs_qa.md` (Contracts, Networks and roles, The loop).

**What to build:** Specialists return small Evidence Packs, and the Coordinator calls the Requerier once per
failed Attempt, so a full 3-Attempt run fits the existing time limits on the cloud model.

**Blocked by:** None (can start immediately)

**Status:** completed (2026-10-16)

**Found in:** the manual re-runs for 09 and 10, nsflow UI, 2026-10-16. Trace: `logs/thinking_dir/Coordinator` and
`logs/thinking_dir/Coordinator.MicrosoftLearnSpecialist`.

**What happened:**

- Dataverse Error Log (14:07): MicrosoftLearnSpecialist finished its searches and one page fetch 14 s in, then
  spent 76 s writing its Evidence Pack and was cancelled at its 90 s limit. The user got "Microsoft Learn is
  unavailable", although Microsoft Learn was up.
- PCF question (13:47): the loop reached Attempt 3, then the Coordinator hit its 480 s limit during Attempt 3's
  Verifier call. The user got no reply.
- In the same PCF run, after Attempt 1 the Coordinator called the Requerier twice. The second call passed one of
  the first call's Requeries as `evidence_pack`. It cost 31 s.
- The common cause: the cloud model is slow to write long JSON. The Specialist writes every quote verbatim, and the
  Coordinator writes the whole pack out again for the Verifier and for the Requerier. No instruction limits how
  many excerpts a pack has or how long a quote is.

**Acceptance criteria:**

- [x] Both Specialists' instructions: at most 6 excerpts, and each quote is only the sentences or code lines that
      back its claim, never a whole page or section. Quotes stay verbatim.
- [x] Coordinator step 4g: call the Requerier once per failed Attempt, with the whole failed pack. Never call it
      again on its own Requeries.
- [x] The spec's Contracts (excerpts) and Requerier role say the same.
- [x] `ns validate` passes.

This is an instruction change only. No new fixture. Time limits stay as they are; raise them only if small packs
are not enough.

**Notes:**

- Both Specialists' Rules gain: "Keep the pack small: at most 6 excerpts. Each quote is only the sentences or code
  lines that back its claims, never a whole page or section."
- Coordinator step 4g: call the Requerier once per failed Attempt with the whole failed pack, never again on its
  own Requeries.
- Spec: the Contracts `excerpts` line and the Requerier role say the same.
- `ns validate` and unit tests passed (110, 2026-10-16). Not checked with an LLM run yet. To check: re-run the
  Dataverse log and the PCF question in the UI and compare the times with 104 s (Specialist timeout) and 480 s
  (Coordinator timeout).
- Live check, 2026-10-16 14:17 (Dataverse log, new instructions loaded): MicrosoftLearnSpecialist still timed out
  at 90 s, so the user got the Microsoft Learn unavailable reply again. Timeline:
  - 14:17:38 start, two searches done by 14:17:41;
  - 14:17:45 `microsoft_docs_fetch` of `power-apps/developer/data-platform/reference/web-service-error-codes`
    took 26 s and returned about 745 KB, the full Dataverse error-code list;
  - a second fetch (the client-errors page, 14 KB) and two more searches by 14:18:37;
  - 31 s writing the pack, then cancelled at 14:19:08.
  - Every LLM call after the big fetch carries that page, so the cause here is the fetch, not the pack size.
  The pack-size rule did not get a fair test.
