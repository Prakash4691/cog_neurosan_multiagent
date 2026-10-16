# 07: Unavailable Source

Spec: `docs/spec/docs_qa.md` (Unavailable Source, Manual check).

**What to build:** when a documentation source fails (rate limit, timeout, error), the user is told plainly. It
never costs a retry, and work already done isn't thrown away.

**Blocked by:** 06

**Status:** completed (2026-10-16). The Cross-domain manual run ended as an Unverified Answer, not a verified
half, because of the Grounded Check tuning that 06 leaves open (see Notes).

- [x] A Specialist whose MCP calls fail returns status UNAVAILABLE with the error kind. Tools that work but find
      nothing return status OK with no Excerpts.
- [x] The Coordinator applies the spec's three cases, and none of them triggers a Requery:
  - single source, fails on Attempt 1;
  - source fails on Attempt 2 or 3;
  - Cross-domain Question with one source down.
- [x] There is no automatic retry.
- [x] The Context7 Specialist's URL can be overridden by an optional `CONTEXT7_MCP_URL` environment variable, using
      HOCON's `${?VAR}` syntax in the network HOCON (not in the MCP server config, whose URLs are keys and can't be
      substituted). When the variable is unset, the URL is the default.
- [x] Run the manual dead-port check from the spec once, and record in this ticket:
  - the single-source result;
  - the Cross-domain result;
  - that behavior returns to normal after unsetting the variable;
  - whether MCP connection failures are retried by the Specialist's `max_attempts` before UNAVAILABLE is reported.
- [x] The `rate_limit` error kind is not exercised in v1. The dead port simulates a connection failure, not a 429.
- [x] `ns validate` passes.

**Notes from 06:**

- The Coordinator's step 4b still stops at any non-OK pack on any Attempt, and step 4a treats a Specialist that
  returns no pack (an error or its own 90 s timeout) as UNAVAILABLE. So an outage on Attempt 2 or 3 discards the
  earlier Attempts. This ticket's "Source fails on Attempt 2 or 3" case replaces that. It was seen in the
  `unverified_ungroundable_question` fixture (a Specialist timeout in Attempt 3).

**Notes:**

- Unit test: `tests/unit/test_context7_mcp_url.py` checks the override (set and unset) through neuro-san's own
  network loader, and that the default URL is a key in `mcp/mcp_info.hocon`.
- Found without the LLM: a dead port fails when neuro-san **loads** the MCP tools, not when one is called.
  `base_tool_factory.create_mcp_tool` catches the `ExceptionGroup` (`ConnectError: All connection attempts
  failed`, checked against `http://localhost:9/mcp`), logs "The URL ... was unreachable. Not including it as a
  tool." and the Specialist runs with no tools. So both Specialists now also return UNAVAILABLE (`error_kind:
  error`) when they have no documentation tools. Before this, they would likely have returned OK with no Excerpts,
  which leads to a Requery.
- `max_attempts` and connection failures: no exception reaches the agent, so the Specialist's `max_attempts`
  doesn't retry a connection failure (confirmed by the manual check below). A failure in a tool call
  after loading comes back to the LLM as "Error: ..." tool output (`McpToolErrorHandler`), and is not retried
  either.
- Coordinator changes (step 4b):
  - A source that is unavailable is not called again for the Question.
  - Requeries suggested for it are dropped. If every Requery is dropped, the loop ends with the Unverified
    Answer.
  - `unavailable_parts` carries over to every later Attempt's pack.
- The Requerier never asks for an unavailable part.
- Fixed reply markers, for later fixtures:
  - "Sorry, I can't answer this right now: <source> is unavailable. Please try again later." (Attempt 1, no answer);
  - "<source> became unavailable, so I could not check this answer again." (Attempt 2 or 3);
  - "Not answered: <part>. <source> is unavailable." (Cross-domain).
- Manual check (2026-10-16, `CONTEXT7_MCP_URL=http://localhost:9/mcp`, one direct AgentCli run each):
  - **Single source** ("In React, how do I run cleanup code in a useEffect hook when the component unmounts?"):
    - Reply: "Sorry, I can't answer this right now: Context7 is unavailable. Please try again later."
    - No answer, no Requery and no Verifier call. 8 s.
    - On the first run, the Specialist had no tools and replied in prose ("let me resolve the React library
      ID") instead of returning a pack. The Coordinator still read that as UNAVAILABLE. Two fixes followed:
      - each Specialist now checks its tools first and returns the UNAVAILABLE pack at once;
      - the Coordinator counts any reply that is not an Evidence Pack as UNAVAILABLE.
    - On the rerun, the Specialist returned `{"source": "context7", "status": "UNAVAILABLE", "error_kind": "error",
      ...}`.
  - **Cross-domain** (React fetch + Azure Functions CORS), 434 s:
    - Context7 was called once, in Attempt 1, and never again.
    - Every Attempt's pack carried `unavailable_parts` with the fetch part. The Verifier's reasons say that part
      was not judged.
    - Both Requerier outputs asked only about the Microsoft Learn part, so no Requery had to be dropped.
    - The reply starts "Not verified: GROUNDED failed ...", then "Not answered: How do I call an HTTP endpoint
      ... with fetch from a React component? ... Context7 is unavailable. Please try again later."
    - The Microsoft Learn half failed Grounded in all 3 Attempts: answer statements no claim covered, and
      claims stating more than their excerpts. This is the open Grounded tuning from 06, not the outage. The
      Requeries also widened the subject (slots, PowerShell), the same tuning area.
    - Attempt 1 logged two "Invoking `__docs_qa__verifier`" lines 7 s apart, but only one Verdict came back.
      Attempts 2 and 3 called it once each.
  - **Variable unset** (same single-source question), 173 s:
    - Context7 tools loaded and worked.
    - Verdicts were INVALID, INVALID, VALID. The reply ends "Verified against 10 documentation Excerpts."
      with 4 Context7 sources.
    - `.env` sets `CONTEXT7_API_KEY`, so this ran keyed.
  - `max_attempts`: each dead-port Specialist logged "The URL http://localhost:9/mcp was unreachable" once, and
    no second Specialist instance started for it. A connection failure is not retried.
  - The "Source fails on Attempt 2 or 3" case was not run: the dead port fails from Attempt 1. It is covered
    only by the Coordinator's instructions.
