# Spec: docs_qa — grounded documentation and error-log assistant

Status: ready-for-agent

Vocabulary follows `GLOSSARY.md`. Architecture follows ADR 0001 (the Coordinator owns the loop), ADR 0002
(redaction happens in middleware before any LLM), ADR 0003 (the Verifier is a separate network) and ADR 0004 (the
loop runs in the `attempt_loop` coded tool).

## Problem Statement

A developer stuck on a technical question, or on an error they can't explain, has two bad options:

- Search the documentation by hand. That is slow, and the docs are spread across Microsoft Learn and many library
  sites.
- Ask a general-purpose LLM. It may answer from out-of-date training data, mix up framework versions, or invent APIs
  that don't exist, with nothing to show which.

Pasting an error log into an AI tool adds a third risk. Logs often contain connection strings, tokens, keys and
internal hostnames, and those would go to third-party services.

The developer wants an answer they can trust: taken from current official documentation, checked against their
actual question, honest when it can't be checked, and safe for pasted logs.

## Solution

A neuro-san multi-agent assistant answers developer questions and resolves error logs using only official
documentation:

- Microsoft Learn for products documented there.
- Context7 for other libraries and frameworks.

Every answer comes with verbatim Excerpts from the documentation retrieved in the same run. A separate Verifier
checks it before the user sees it: is it grounded in the Excerpts, does it match the asked framework and version,
and, for error logs, does it give a root cause and a fix?

If the Verifier rejects an answer, the Question is rewritten or split and tried again, up to 3 Attempts. If every
Attempt fails, the user gets the best attempt, clearly marked as unverified, with the reason. Questions no
documentation source can ground are declined politely. Secrets in pasted logs are redacted before any LLM sees
them, and only a short Error Signature goes to the documentation servers.

## User Stories

### Asking questions

1. As a developer, I want to ask a question about an Azure service and get an answer from Microsoft Learn, so that I
   get Microsoft's current guidance instead of model memory.
2. As a developer, I want to ask about React, Go, Java or another library and get an answer from that library's
   current documentation, so that the answer reflects the version I use.
3. As a developer, I want a question that involves both a Microsoft product and a third-party library (for example a
   React app calling Azure Functions) to be answered from both sources in one reply, so that I don't have to ask
   twice.
4. As a developer, I want questions about Microsoft-owned projects documented outside Microsoft Learn (TypeScript,
   VS Code extension APIs) to go to the source that actually documents them, so that routing follows where the docs
   live, not who makes the product.
5. As a developer, I want GitHub Actions questions about Microsoft product integrations (Azure, .NET, Power Platform)
   answered from Microsoft Learn, and plain workflow-syntax questions answered from library documentation, so that
   each part of GitHub Actions comes from its authoritative source.
6. As a developer, I want a question the assistant can't place with confidence to be sent to both sources, so that
   an uncertain route never means a wrong-source answer.
7. As a developer, I want to name a framework version in my question and get an answer for that exact version, so
   that I don't apply guidance for the wrong release.
8. As a developer who doesn't name a version, I want the answer to say which version it covers, so that I can tell
   whether it applies to me.
9. As a developer, I want to ask a follow-up ("what about on Linux?") without restating the context, so that the
   conversation feels natural.
10. As a developer, I want a follow-up to be checked against what I actually meant, the standalone form of my
    follow-up, so that verification stays accurate across turns.

### Error logs

11. As a developer, I want to paste a stack trace or compiler error and get a likely root cause and concrete fix
    steps, so that I can get unblocked.
12. As a developer, I want the fix to be tied to the specific error type, code and message in my log, so that I get
    a resolution for my error rather than generic advice.
13. As a developer, I want the library and version in my log to be used when looking up docs, so that the fix
    matches my environment even when I didn't state the version.
14. As a developer, I want connection strings, tokens, API keys, private keys, secret assignments, emails and
    internal hostnames in my pasted log to be redacted before any LLM sees them, so that my credentials don't leak
    to cloud services.
15. As a developer, I want public cloud hostnames (such as `*.azurewebsites.net`) kept in my log, so that details
    that matter for diagnosis are not lost.
16. As a developer, I want only a short Error Signature, not my raw log, sent to the documentation servers, so that
    third-party search services see the minimum, and search works better.

### Verification and trust

17. As a developer, I want every key claim in an answer to be backed by a verbatim Excerpt from documentation fetched
    for my question, so that I can trust the answer isn't invented.
18. As a developer, I want numbered source links with every answer, so that I can read the original documentation.
19. As a developer, I want a verified answer to say how many Excerpts it was checked against, so that I can see
    the evidence behind it.
20. As a developer, I want an answer for the wrong framework or version rejected and retried, so that I'm not
    misled by a close-but-wrong answer.
21. As a developer, I want an error-log answer with no root cause or no fix rejected and retried, so that I get
    something I can act on.
22. As a developer, I want a rejected answer to lead to a rephrased or split version of my question, so that a
    poor first search doesn't decide the outcome.
23. As a developer, I want the number of retries capped, so that I get a reply within a reasonable time even when
    the docs don't cover my question well.
24. As a developer, I want the best attempt returned with a clear "not verified" warning and the reason when every
    attempt fails, so that I still get something useful and know how far to trust it.
25. As a developer, I want the assistant never to fill gaps from model memory when documentation is missing or
    unreachable, so that every answer it gives is grounded.

### Scope and failures

26. As a developer, I want questions no documentation source can ground (the weather, my own business logic)
    declined in one polite sentence that says what the assistant covers, so that I know where its limits are and
    am never given an ungrounded answer.
27. As a developer, I want to be told plainly when a documentation source is unavailable (rate limit, timeout,
    error), so that I can retry later instead of getting a degraded answer.
28. As a developer with a Cross-domain Question where one source is down, I want the verified half of the answer
    plus a note naming the part that couldn't be answered, so that the outage costs me as little as possible.
29. As a developer, I want a source outage after an earlier failed Attempt to return the best earlier attempt as
    unverified with an "unavailable" note, so that the work already done isn't thrown away.
30. As a developer, I want a source outage never to use up retries, so that time isn't spent rephrasing a question
    the source can't answer anyway.
31. As a developer using the web UI, I want a hung request to fail with an error after a fixed limit, so that the
    UI never waits forever.

### Maintainer

32. As the maintainer, I want to run a golden set of known-valid and known-invalid Evidence Packs against the
    Verifier on its own, so that I can measure how reliable the Verifier is and catch regressions when I change its
    prompt or model.
33. As the maintainer, I want each Verdict to list the failed Checks and the reason before VALID or INVALID, so that
    the Verifier reasons before deciding and its output can be checked by a script.
34. As the maintainer, I want a deterministic test proving the redaction rules redact every secret class and leave
    public hostnames alone, so that a regex change can't silently weaken privacy.
35. As the maintainer, I want an end-to-end test proving the redaction is wired to the Coordinator in the deployed
    network, so that a config mistake can't silently turn privacy off.
36. As the maintainer, I want a deterministic test for Error Signature extraction, so that changes to log parsing
    are safe.
37. As the maintainer, I want a documented way to make a documentation source fail on demand, so that I can check
    the Unavailable Source behavior without waiting for a real outage.
38. As the maintainer, I want both documentation servers to work without API keys, so that the assistant runs on a
    fresh machine with no secret setup.
39. As the maintainer, I want every agent bounded by step and wall-clock limits, so that a looping model can't run
    forever or run up cost.
40. As the maintainer, I want an LLM provider error on the Coordinator to surface as an error rather than silently
    restart the whole loop, so that worst-case latency and cost stay bounded.

## Implementation Decisions

### Networks and roles

- **`docs_qa/assistant`** is the network users talk to. It holds four agents and two coded tools:
  - the Coordinator (Front Man);
  - the Microsoft Learn Specialist;
  - the Context7 Specialist;
  - the Requerier;
  - `log_signature_extractor` (see Error logs);
  - `attempt_loop`, which runs the loop (ADR 0004).
- **`docs_qa/verifier`** is a separate network holding only the Verifier (ADR 0003).
  - It is listed in the manifest as served but not public: callable and testable, but hidden from the UI list.
  - `attempt_loop` calls it through a same-server reference.
- **Hub topology (ADR 0001, ADR 0004).** One place owns the original Question and the loop, and no LLM agent calls
  another agent.
  - The Coordinator's LLM makes the judgment calls: it writes the standalone Question, gets the Error Signature,
    chooses the Specialists and the part each gets, declines Out-of-scope Questions, and writes the reply.
  - It then calls `attempt_loop` once. That coded tool calls the Specialists, the Verifier and the Requerier, counts
    Attempts, merges Evidence Packs, chooses the Unverified Answer, and numbers the sources. It returns the parts of
    the reply, without the Excerpts' quotes, so Evidence Packs never pass through the Coordinator's LLM.
- **Specialists:**
  - Each Specialist has exactly one MCP server.
  - Each Specialist's instructions encode that server's call order:
    - Microsoft Learn: search, then code-sample search or fetch as needed. At most 5 tool calls: up to 3 searches,
      one code-sample search and one fetch, and never a fetch of a long reference page such as a list of all error
      codes.
    - Context7: resolve the library ID, then query the docs, up to 3 queries.
  - A Specialist searches once for each thing the Question asks. When the Question asks for prerequisites,
    requirements, permissions or limits, it always searches for them on their own, because a task's own page often
    lists only some of them. It uses excerpts from every page that answers part of the Question.
  - A claim keeps the conditions the documentation gives for it, such as a requirement that applies only with one
    kind of host. A condition, exception or consequence of something the answer says is part of it, not an extra.
  - The Verifier judges only against the pack's Excerpts, so it can't see what a narrow search missed. Breadth is
    the Specialist's job.
  - A Specialist must never answer from model memory.
- **Requerier:**
  - It is internal to the assistant network, with no network of its own.
  - It receives the original Question, the failed Evidence Pack and the Verdict's reason.
  - It is called once per failed Attempt, never on its own Requeries.
  - It returns one or more Requeries, each with a suggested Specialist.
  - It keeps every product, library, client and version name the Question uses, even one the documentation does
    not mention, and never swaps in another product.
  - It never answers.

### Routing

- **The rule is where the documentation lives, not who makes the product** (see the Specialist coverage entries in
  the glossary).
  - Products documented on Learn go to the Microsoft Learn Specialist: Azure including AKS, .NET and C#, M365 and
    Graph, Windows, Power Platform, SQL Server, Entra, and GitHub Actions used with those products.
  - Everything else goes to the Context7 Specialist, including TypeScript, VS Code extension APIs, plain GitHub
    Actions workflow syntax, general GitHub and plain Kubernetes.
- **Cross-domain and uncertain Questions** go to both Specialists, and their Evidence Packs are merged with every
  Excerpt kept.
- **Out-of-scope Questions** are declined by the Coordinator in one polite sentence, without calling any Specialist.
  They are never answered.
- **Follow-ups.** The Coordinator rewrites a follow-up into a standalone Question using the conversation history.
  Specialists and the Verifier never see the history.

### The loop

- **One Attempt** means:
  1. Send the Question, or the Requeries, to Specialists.
  2. Collect the Evidence Packs and merge them.
  3. Send the merged pack to the Verifier.

  Sub-questions from one Requerier output together count as a single Attempt.

- **The loop ends at the first of:**
  - a VALID Verdict, which returns the verified answer;
  - the end of the 3rd Attempt, which returns the Unverified Answer;
  - an Out-of-scope Question, which gets an immediate decline;
  - an Unavailable Source, under the rules below;
  - a Requerier that returns no Requeries (an error, a timeout or an empty list), which returns the Unverified
    Answer from the attempts so far;
  - the loop's time budget of 360 seconds, which returns the Unverified Answer from the attempts so far with the
    note "I ran out of time to look this up again, so this is the best answer I found." If no Attempt finished,
    the reply is "Sorry, I couldn't finish looking this up in time. Please try again." (outcome `unavailable`).
- **The Verifier always judges against the original Question** (or the standalone follow-up), never against a
  Requery. Splitting a question can't change what success means.
- **Choosing the Unverified Answer.** Among the failed attempts, pick the one with the fewest failed Checks. A failed
  Grounded Check counts most. If two attempts tie, the later one wins.
- **The loop is code (ADR 0004).** `attempt_loop` enforces the Attempt cap, the one-call-per-Question rules and
  the Unavailable Source rules and the time budget. The step and time limits are the backstop.
- **Specialists in one Attempt run concurrently.**
- **Mechanical checks run before the Verifier.** A pack with no Excerpts, no claims, a claim that cites no Excerpt
  or an unknown one, or no stated `version_covered`, is INVALID without a Verifier call. Its Verdict lists only those
  failed Checks.
- **The Requerier gets the failed pack without the Excerpts' quotes.** It needs the claims, the version and the
  unavailable parts, not the documentation text.

### Unavailable Source

- A Specialist whose MCP calls fail (rate limit, timeout, error) returns status UNAVAILABLE with the kind of error.
  This is not a Verdict and never triggers a Requery. There is no automatic retry in v1.
- An MCP server that can't be reached fails before any call: neuro-san drops its tools when it loads them, and the
  Specialist runs with no tools. The Specialist's instructions treat having no documentation tools as UNAVAILABLE
  with `error_kind: error`.
- Once a source is unavailable, `attempt_loop` doesn't call its Specialist again for that Question, and drops
  any Requery suggested for it. The Requerier never asks for a part listed in `unavailable_parts`.
- Only a Specialist called for the current Question can be unavailable. Packs and replies from earlier turns never
  count.
- Tools that work but return nothing useful are **not** UNAVAILABLE. The result is status OK with no Excerpts, which
  fails the Grounded Check and leads to a Requery.
- What happens depends on when and where the source fails:

  | Case                                              | What the user gets                                                                                                                                                                        |
  | ------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
  | Single-source Question, source fails on Attempt 1 | A reply naming the unavailable source and suggesting they retry later. No answer.                                                                                                         |
  | Source fails on Attempt 2 or 3                    | The best earlier attempt as an Unverified Answer, with a "source became unavailable" note.                                                                                                |
  | Cross-domain Question, one source fails           | The merged pack lists the part that couldn't be answered. The Verifier judges only the covered parts. The user gets the verified half plus a note naming the missing part and its source. |

### Contracts

These shapes were decided in the design discussion, not by a prototype. They are given as shapes because a
shape is more exact than prose here.

The Evidence Pack, which every Specialist returns and `attempt_loop` merges:

```
source:            ms_learn | context7            (set by attempt_loop; merged pack: per-claim / per-excerpt source)
status:            OK | UNAVAILABLE  (+ error_kind: rate_limit | timeout | error)
version_covered:   e.g. "React 19.1" | "not version-specific"
answer:            text
claims:            [{ id, text, excerpt_ids: [...] }]
excerpts:          [{ id, url, quote }]           (verbatim, retrieved in this Attempt only; at most 6 per
                                                   Specialist pack, each quote only the lines that back a claim)
unavailable_parts: [{ part, source, error_kind }] (Cross-domain Question with one source down only)
```

A merged pack's `version_covered` names each source's, such as "Microsoft Learn: not version-specific; Context7:
React 19.1". If any pack leaves it empty, the merged one is empty too.

What `attempt_loop` returns to the Coordinator:

```
outcome:             verified | not_verified | unavailable
reply:               the whole Unavailable Source reply              (unavailable only)
not_verified_reason: the chosen Attempt's Verdict reason            (not_verified only)
notes:               fixed lines: "<source> became unavailable, ..." and "Not answered: <part>. ..."
answer:              the pack's answer
claims:              [{ text, sources: [1, 2] }]                    (numbered by page URL without its #section, in order of first citation)
version_covered:     text
sources:             "Sources:" and the numbered URLs, each labelled (Microsoft Learn) or (Context7); empty if none
footer:              "Verified against N documentation Excerpts."   (verified only)
```

The Verdict, which the Verifier returns, with fields in this order:

```
failed_checks:  subset of [GROUNDED, RELEVANT, ACTIONABLE], possibly empty
reason:         text, written before the verdict
verdict:        VALID | INVALID
```

**The Checks** (all must pass for VALID):

- **Grounded:**
  - every claim cites at least one Excerpt;
  - each cited Excerpt actually supports the claim;
  - the answer makes no factual statement that isn't in `claims`.
- **Relevant:** the answer matches the exact framework and version in the Question or the Error Signature. If
  neither names a version, `version_covered` must be stated, and the answer can't fail on version alone.
- **Actionable:** for Error Log Questions, the answer names a root cause and a fix tied to the Error Signature.
  For documentation questions, it gives the specific API, config or steps that were asked for.

**The Verifier network's interface:**

- Its Front Man declares exactly two parameters: `question` (a string) and `evidence_pack` (an object in the
  shape above).
- neuro-san delivers these to the Front Man as a fenced JSON block of the tool-call arguments.
- Without declared parameters, neuro-san would make up a single `inquiry` string.
- No `sly_data` reaches the Verifier, so everything it needs is in those two arguments.
- The Verifier has no tools and never re-fetches URLs in v1. The Excerpts are the evidence.

### Error logs and secret redaction (ADR 0002)

- **Redaction runs first.** The Coordinator runs LangChain `PIIMiddleware` (confirmed present in langchain 1.4.5)
  with `strategy: redact` and `apply_to_input: true`, so the user's message is redacted before the first LLM call.
  There are seven entries: six custom `pii_type` names, each with a regex `detector`, plus the built-in `email`.
  Each entry is an `AllTurnsPIIMiddleware`: a `PIIMiddleware` subclass that takes the same args but redacts every
  user message in the conversation. neuro-san sends the raw chat history with each new turn, and plain
  `PIIMiddleware` redacts only the newest message, so a secret from an earlier turn would reach the LLM.

  | pii_type            | Covers                                                                                         |
  | ------------------- | ---------------------------------------------------------------------------------------------- |
  | `connection_string` | ADO.NET/ODBC password and account-key pairs, URIs with credentials (postgres, mongodb, JDBC)   |
  | `bearer_token`      | Authorization Bearer headers, JWTs                                                             |
  | `cloud_key`         | Azure account keys and SAS signatures, AWS access key IDs, GitHub tokens, `sk-` style API keys |
  | `secret_assignment` | `password=`, `api_key:`, `client_secret=`, `token=` style key-value pairs                      |
  | `private_key`       | PEM private key blocks                                                                         |
  | `internal_host`     | `.local`, `.internal`, `.corp`, `.lan` hostnames, and private IPv4 ranges                      |
  | `email`             | built-in                                                                                       |

  Public cloud hostnames are not redacted.

- **`log_signature_extractor`** is a deterministic coded tool.
  - The Coordinator calls it on the already-redacted log before routing.
  - It returns only the Error Signature: error type or code, message, library and version, and the top relevant
    frames.
  - It does no redaction. The regexes stay in the middleware config, and moving them into the tool would bring back
    the cloud-LLM leak (ADR 0002).
- **Only the Error Signature** is passed to Specialists and MCP servers. The raw log never leaves the Coordinator.

### MCP servers

- **Both servers are registered keyless,** each with a tool allow list:
  - Microsoft Learn: three tools — docs search, code-sample search and docs fetch.
  - Context7: two tools — resolve library ID and query docs.
  - Context7 runs at its anonymous rate limit by default. An optional `CONTEXT7_API_KEY` environment variable
    adds a key for higher limits. The anonymous monthly quota ran out during the first loop runs.
- **Overridable Context7 URL.** The Context7 Specialist reads its server URL from a network-level HOCON value that
  defaults to the public Context7 endpoint. An optional `CONTEXT7_MCP_URL` environment variable overrides it, using
  HOCON's `${?VAR}` syntax. This override exists only for the manual Unavailable Source check (see Testing). Checked
  with neuro-san's own HOCON loader: when the variable is set it replaces the URL, and when it is unset the default
  stays.

### Limits

| Agent       | `max_steps` | `max_execution_seconds` | `max_attempts` |
| ----------- | ----------- | ----------------------- | -------------- |
| Coordinator | 240         | 480                     | 1              |
| Specialists | 20          | 120                     | default (3)    |
| Verifier    | 10          | 120                     | default (3)    |
| Requerier   | 10          | 120                     | default (3)    |

- The Coordinator uses `max_attempts = 1` because a retryable LLM error would otherwise re-run the whole loop from
  the start.
- The Coordinator's `max_steps` is LangGraph's recursion limit, not a count of LLM calls. Each of its 7 redaction
  middleware entries adds a `before_model` and an `after_model` step to every LLM call, so one tool round costs
  about 16 steps. The first runs hit the original limit of 60 during Attempt 2, and 240 covered about 210 steps when
  the loop was in the prompt. With the loop in `attempt_loop`, an Error Log takes about 4 rounds. 240 stays as a
  loose backstop until a measured run.
- `attempt_loop` runs inside the Coordinator's 480 seconds. Each Specialist, Verifier and Requerier call it makes
  is still bounded by that agent's own limit.
- `attempt_loop` stops the loop after 360 seconds (`LOOP_SECONDS`) and returns its best Attempt. Without it, a slow
  3-Attempt run reaches the Coordinator's 480 seconds and the user gets no reply (issue 14). The other 120 seconds
  are for the Coordinator's own LLM rounds before and after the loop. A unit test checks that the budget leaves
  those 120 seconds and that Attempt 1 (a Specialist plus the Verifier, 240 seconds at most) always fits in it.
- The Specialists' limit was raised from 90 to 120 seconds when they began to search once per part of the
  Question (issue 16). The loop budget, not the Specialists' limit, bounds the whole run.
- The assistant network sets `request_timeout_seconds = 540` as a top-level key. The server enforces it on HTTP
  chat requests only (the nsflow UI and the HTTP API). A direct in-process `ns chat` session doesn't enforce it, and
  there the Coordinator's 480-second `max_execution_seconds` is the guard.
- The time limits were raised after the first loop runs (originally Coordinator 300, request 360, Verifier 60). A
  3-Attempt run took about 370 seconds while the Coordinator's LLM wrote each Evidence Pack out again for the
  Verifier and the Requerier (before ADR 0004), and the Verifier timed out at 60 seconds on a merged pack of three
  Requery answers.
- The Requerier's limit was raised from 60 to 120 seconds after manual testing, where it timed out in 2 of 3 calls
  on large Evidence Packs (one call that finished took 17 seconds). The Coordinator's 480 seconds stays: a run where
  both Requerier calls are slow can still reach it.

### User-facing reply shapes

| Reply type            | What it contains                                                                                                                                                                                                                           |
| --------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| Verified answer       | The answer, numbered source links each labelled with its source (Microsoft Learn or Context7), and a footer saying it was verified against N documentation Excerpts. Excerpts themselves are not shown.                                    |
| Unverified Answer     | The same as a verified answer, without the footer, plus a warning line at the top: "Not verified: " and one or two plain sentences, based on that Attempt's Verdict reason, with no claim or excerpt ids, Check names or JSON field names. |
| Out-of-scope Question | One polite sentence saying what the assistant covers.                                                                                                                                                                                      |
| Unavailable Source    | Which source is unavailable, and a suggestion to retry later. Plus any verified partial answer (see Unavailable Source above).                                                                                                             |

### Dependencies

- `pytest` is added as a dev-only dependency. No runtime dependencies are added.

## Testing Decisions

**What makes a good test here:**

- Test what a caller can observe at a network's entry point or a tool's interface: the reply, the Verdict, the
  Error Signature, the redacted text.
- Never test internal prompts or which tool an agent happened to call.
- LLM-backed tests:
  - assert with `keywords`, `not_keywords` or `gist`;
  - set a `success_ratio` so a single nondeterministic miss doesn't fail the test;
  - set `use_direct = true` for the assistant, so the test driver calls `/docs_qa/verifier` in-process. Without
    it, the driver looks for the Verifier over HTTP on a running server, the Verifier call fails, and every
    answer comes back unverified;
  - set `timeout_in_seconds = 540` for the assistant (the Coordinator's 480 seconds plus headroom), and 360 for the
    Verifier.
- Deterministic code gets exact assertions.

**Seams:**

1. **The `docs_qa/assistant` entry point** (neuro-san data-driven HOCON fixtures). Cases:
   - Microsoft Learn routing (an Azure question);
   - Context7 routing (a React or Go question);
   - a Cross-domain Question;
   - an Error Log, where the reply names a root cause and a fix;
   - an Out-of-scope Question (polite decline, no answer);
   - a follow-up turn;
   - the shapes of a verified and an unverified reply;
   - **a planted-secret fixture:** the input log contains a fake connection string, token and key, and
     `not_keywords` on the reply asserts that none of them comes back. This proves the middleware is actually wired
     to the Coordinator in the deployed network.
2. **The `docs_qa/verifier` entry point** (data-driven fixtures, the golden set).
   - Each fixture sends the same fenced JSON block of `question` and `evidence_pack` that real tool calls send, and
     asserts on `verdict` and `failed_checks`.
   - The golden set has at least one known-invalid case for each Check, plus known-valid cases, including one with
     no version stated and one Cross-domain pack with `unavailable_parts`.
   - The maintainer writes the golden set's contents. The build creates the fixture skeletons and format.
3. **`log_signature_extractor` and `attempt_loop` unit tests** (pytest, deterministic). `attempt_loop` is driven
   by scripted agent replies and covers the loop, merge, Unverified Answer, Unavailable Source and source-numbering
   rules. `log_signature_extractor`: Error Signature extraction for several log
   types (.NET exception, Java stack trace, Go panic, Node/npm error, compiler error). The input logs are already
   redacted.
4. **Redaction detector unit tests** (pytest, deterministic).
   - Load the detector regexes from the assistant network's HOCON, the same config that is deployed, and run
     `PIIMiddleware` on sample logs.
   - Assert that every secret class is redacted, and that public cloud hostnames and ordinary log text are not.
   - This proves the regexes redact. Seam 1's planted-secret fixture proves they are wired in. The two are kept
     separate on purpose.

**Manual check: Unavailable Source** (no automated test in v1). To make Context7 fail on demand:

1. Set `CONTEXT7_MCP_URL` to a URL that points at a dead local port and still contains an `/mcp` path segment, so
   neuro-san recognizes it as an MCP server. For example, port 9 on localhost with path `/mcp`.
2. Run a single-source Context7 Question. Expect: a reply naming Context7 as unavailable, with no answer and no
   Requery.
3. Run a Cross-domain Question. Expect: the verified Microsoft Learn half, plus a note that the library part couldn't
   be answered.
4. Unset the variable and confirm normal behavior returns.

This step also answers an open question: whether MCP tool failures go down the Unavailable Source path or get
retried by the Specialist's `max_attempts`.

`MCP_SERVERS_INFO_FILE` can't be used for this, for two reasons:

- That file supplies headers and tool allow lists keyed by URL. It doesn't change which URL an agent calls.
- Its URLs are HOCON keys, and HOCON can't substitute environment variables into keys. (Values can be
  substituted, which is how the header comments use `${VAR}`.)

So the override lives in the network HOCON. Two consequences:

- The network's default Context7 URL must match the URL key in the MCP server config exactly. Otherwise the tool
  allow list silently stops applying.
- While the dead URL is in use, the allow list doesn't apply. That doesn't matter, because the connection fails
  anyway.

The dead port only simulates a **connection failure**. It doesn't produce an HTTP 429 rate-limit response, so the
`rate_limit` error kind is not exercised in v1, automatically or by hand. Only `error` (and `timeout`, if the
connection hangs instead of being refused) is checked.

**Prior art:**

- This repo has no tests yet.
- Copy the fixture format from upstream neuro-san-studio's integration fixtures, documented in neuro-san's test
  case HOCON reference.
- Copy the pytest layout from upstream's unit tests for coded tools.

## Out of Scope

These are decided for v1, so the build should not re-open them:

- **No organization-specific domain suffixes in the redaction regexes.** The generic internal-host list stands. The
  maintainer may add private suffixes later.
- **No required API keys for either MCP server.** Both run keyless by default, and Context7 at its anonymous rate
  limit. A Context7 key is optional, read from `CONTEXT7_API_KEY`.
- **No re-fetching of URLs by the Verifier.** The Excerpts are the grounding evidence.
- **No automatic retry when a source is unavailable.**
- **No answers to Out-of-scope Questions.** That includes answers from model knowledge, even when labelled.
- **No custom redaction logic.** Redaction is `PIIMiddleware` config. The only custom class is
  `AllTurnsPIIMiddleware`, which applies the same config to earlier turns too. A custom class that also swaps the
  log for its signature was considered and deferred (ADR 0002).
- **No redaction before the user's message reaches the server.** Redaction starts at the Coordinator's first
  model call.
- **No Attempt counter in code.** Revisit only if testing shows the model overruns the cap.
- **No separate network for the Requerier.**
- **No other documentation sources** beyond Microsoft Learn and Context7.
- **No automated test for Unavailable Source.** It is a manual procedure in v1.

## Further Notes

- **The LLM is a cloud model.** Every agent uses the shared `glm-5.3:cloud` model through Ollama Cloud. That's why
  redaction must happen before the Coordinator's first model call, and not in a tool (ADR 0002).
- **The verify loop is slow.** The worst case is about 15–25 LLM calls (fewer since ADR 0004). Tune the step and time limits after the
  first golden-set runs.
- **Questions for the first test runs:**
  - How do MCP tool failures interact with `max_attempts`?
  - Does copying a long redacted log into the extractor's tool call lose anything?
- **Build with the repo's own skills:** `new-agent-network` for both networks and `new-coded-tool` for the
  extractor. Run `ns validate` on each network.
