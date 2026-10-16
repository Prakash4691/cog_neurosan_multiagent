# 12: Coordinator reports a source as unavailable when it was never called

Spec: `docs/spec/docs_qa.md` (Unavailable Source, Routing).

**What to build:** a "not answered" or "unavailable" note appears only for a Specialist that was called in this
turn and returned status UNAVAILABLE.

**Blocked by:** None (can start immediately)

**Status:** completed (2026-10-16)

**Found in:** manual testing in the nsflow UI, 2026-10-16. Trace: `logs/thinking_dir/Coordinator`, the turn that
starts at 12:54:07.

**What happened:**

- The user asked "how can I check this is dataverse pcf component", a follow-up to the React question in turn 1.
- The Coordinator called only MicrosoftLearnSpecialist. Context7Specialist was not called in this turn.
- After the INVALID Verdict, the Coordinator wrote: "Note: Context7 couldn't answer the plain-React part of the
  question, so I'll drop any Requery aimed at it."
- The final reply then said: "Not answered: How to detect from React itself (in plain React documentation)
  whether a PCF control is running in Dataverse. Context7 is unavailable. Please try again later."
- Context7 was up: it answered turn 1 at 12:52. The likely cause is turn 1's Context7 Evidence Pack in the chat
  history, which the Coordinator mixed into this turn. This is a guess, not checked.
- The user is told to retry later for a source that works, and the reply invents a question part the user did not
  ask about.

**Acceptance criteria:**

- [x] The Coordinator's instructions say that `unavailable_parts` and the unavailable-source note come only from
      Evidence Packs returned in the current turn, never from earlier turns.
- [x] `ns validate` passes.

This is an instruction change only. No new fixture.

**Notes:**

- Coordinator step 4b now says only a Specialist called for this Question can be unavailable: packs and replies
  from earlier turns never count, and a Specialist that was not called is never unavailable.
- The spec's Unavailable Source section says the same.
- `ns validate` passed. Not checked with an LLM run yet.
