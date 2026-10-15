# 03: Verifier network and golden-set format

Spec: `docs/spec/docs_qa.md` (Contracts, Checks). ADR 0003.

**What to build:** a stand-alone `docs_qa/verifier` network. Given a Question and an Evidence Pack, it returns a
Verdict, so the maintainer can measure the Verifier against a golden set before it is wired into the loop.

**Blocked by:** 01 (the test tooling only)

**Status:** completed

- [x] The Verifier's Front Man declares exactly two parameters: `question` (string) and `evidence_pack` (an object
      in the spec's shape).
- [x] It returns a Verdict with fields in this order: `failed_checks`, `reason`, `verdict` (VALID/INVALID).
- [x] The Grounded, Relevant and Actionable Checks are applied exactly as the spec defines them, including:
  - an uncited factual statement fails Grounded;
  - a question with no version passes only if `version_covered` is stated;
  - `unavailable_parts` are not judged.
- [x] It has no tools and never re-fetches URLs.
- [x] It is in the manifest as served but not public. `ns validate` passes.
- [x] Golden-set fixture skeletons exist. Each one sends the same fenced JSON block of `question` and
      `evidence_pack` that real tool calls produce, and asserts on `verdict` and `failed_checks`.
- [x] There is at least one skeleton for each of these:
  - known-invalid Grounded;
  - known-invalid Relevant (wrong version);
  - known-invalid Actionable (error log with no fix);
  - known-valid;
  - known-valid with no version stated;
  - Cross-domain with `unavailable_parts`.
- [ ] The maintainer fills in the golden-set contents. This ticket delivers the format and placeholders.
      Pending, maintainer: the 7 cases in `tests/fixtures/docs_qa/verifier/` are realistic placeholders marked
      PLACEHOLDER. All 7 pass against the Verifier (2026-10-15). An added case,
      `invalid_relevant_no_version_stated`, covers an empty `version_covered`.
