# 13: Unverified Answer reason uses internal IDs

Spec: `docs/spec/docs_qa.md` (User-facing reply shapes).

**What to build:** the "Not verified:" warning tells a developer in plain words why the answer could not be
checked, without the Verifier's internal claim and excerpt IDs.

**Blocked by:** None (can start immediately)

**Status:** completed (2026-10-16)

**Found in:** manual testing in the nsflow UI, 2026-10-16. Both Unverified Answers (12:58:13 and 13:18:10) in
`logs/thinking_dir/Coordinator`.

**What happened:**

- The Coordinator's instructions (`registries/docs_qa/assistant.hocon:150`) say the first line is "Not verified: "
  followed by the Verdict reason. The Coordinator pastes the Verifier's `reason` as it is.
- That reason is written for the Verifier's own check and for scripts. It names claim and excerpt IDs and contract
  fields, for example:

  > Not verified: GROUNDED fails for three reasons. (1) Claim c6 cites excerpt id 'c1', which is a claim id, not an
  > id in `excerpts` (only e1-e10 exist) ...

- The user never sees claims or excerpts, so "c6", "e1-e10" and `excerpts` mean nothing to them. The reason is also
  a long paragraph, not one line.

**Decision (2026-10-16):** the Coordinator rewrites the reason for the user. The Verifier and its contract do not
change. This is an instruction change only.

**Acceptance criteria:**

- [x] The Coordinator's instruction for the "Not verified: " line says: one or two plain sentences, based on the
      Verdict reason, with no claim or excerpt IDs, no Check names and no contract field names.
- [x] The spec's Unverified Answer row says the same.
- [x] `ns validate` passes.

**Notes:**

- Coordinator step 7: "Not verified: " is followed by one or two plain sentences based on the Verdict reason, with
  no claim or excerpt ids, no Check names and no JSON field names.
- The spec's Unverified Answer row says the same. Existing fixtures only assert "Not verified:", so they still
  match.
- `ns validate` passed. Not checked with an LLM run yet.
