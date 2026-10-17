# 16: Answers are accurate but too narrow, and a slow loop can end with no reply

Spec: `docs/spec/docs_qa.md` (Networks and roles: Specialists, The loop, Contracts, Limits).

**What to build:** Specialists look up every part of the Question, prerequisites included, within a fixed number of
tool calls. Sources are numbered per page. The loop has a time budget, so a slow run returns its best Attempt
instead of hitting the Coordinator's limit.

**Blocked by:** None (can start immediately)

**Status:** completed (2026-10-17)

**Found in:** a manual run in the nsflow UI, 2026-10-17, `kimi-k3:cloud`. Question: "how to deploy dataverse
solution using power platform pipeline. What are the prerequisite?"

**What happened:**

- The answer was verified, and every claim matched the Microsoft Learn "Run pipelines in Power Platform" page. But
  the Specialist made one search and fetched only that page, so the answer missed prerequisites that are on the
  setup pages:
  - target environments must be Managed Environments;
  - every environment in the pipeline needs a Dataverse database;
  - default and Teams environments can't be targets;
  - deploying to other regions needs cross-geo deployments enabled.
- "The Power Platform Pipelines application must be installed in your pipeline host environment" applies only to
  a custom host. The page states it without that condition, and the setup page that explains it was never
  retrieved.
- The answer kept "deployment stages must be completed in order" but dropped the sentence after it: the version
  deployed to test is what goes to production.
- Sources listed the same page twice: `run-pipeline` (fetched) and `run-pipeline#run-a-pipeline` (a search result).
- The Verifier can't catch any of the gaps: it judges only against the pack's Excerpts (spec, Out of Scope: no
  re-fetching). Breadth has to come from the Specialist.

**Acceptance criteria:**

- [x] Both Specialists search once for each thing the Question asks, and always search for prerequisites,
      requirements, permissions or limits on their own when the Question asks for them.
- [x] Tool calls are capped: Microsoft Learn at most 5 (up to 3 searches, 1 code-sample search, 1 fetch, and never
      a long reference page), Context7 at most 3 queries after resolving the library.
- [x] Both Specialists keep a statement's conditions, exceptions and consequences in the claim.
- [x] `attempt_loop` numbers sources by page URL without the `#section`.
- [x] `attempt_loop` stops the loop at 360 seconds and returns the best Attempt as unverified with a note, or an
      out-of-time reply if no Attempt finished.
- [x] Specialists' `max_execution_seconds` raised from 90 to 120.
- [x] Spec updated. Unit tests for the fragment, both out-of-time cases and the budget against the limits.
- [x] `ns validate` and unit tests pass.

**Notes:**

- Time budget: Coordinator 480 s = loop 360 s + 120 s for its own LLM rounds. Attempt 1 at most 120 s (Specialist) +
  120 s (Verifier) = 240 s, so it always fits. Attempts 2 and 3 run only while time is left. A unit test enforces
  both sums.
- The fetch rule comes from issue 14's live check: a 745 KB error-code page took 26 s to fetch and made every later
  LLM call slow, and the Specialist timed out.
- Not checked with an LLM run yet (Ollama Cloud quota). To check: re-run the Power Platform pipelines question in
  the UI. Expect the Managed Environments and Dataverse prerequisites, prerequisite 5 marked as custom host only,
  one source per page, and a total time under 480 s.
