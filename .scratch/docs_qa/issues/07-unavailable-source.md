# 07: Unavailable Source

Spec: `docs/spec/docs_qa.md` (Unavailable Source, Manual check).

**What to build:** when a documentation source fails (rate limit, timeout, error), the user is told plainly. It
never costs a retry, and work already done isn't thrown away.

**Blocked by:** 06

**Status:** ready-for-agent

- [ ] A Specialist whose MCP calls fail returns status UNAVAILABLE with the error kind. Tools that work but find
      nothing return status OK with no Excerpts.
- [ ] The Coordinator applies the spec's three cases, and none of them triggers a Requery:
  - single source, fails on Attempt 1;
  - source fails on Attempt 2 or 3;
  - Cross-domain Question with one source down.
- [ ] There is no automatic retry.
- [ ] The Context7 Specialist's URL can be overridden by an optional `CONTEXT7_MCP_URL` environment variable, using
      HOCON's `${?VAR}` syntax in the network HOCON (not in the MCP server config, whose URLs are keys and can't be
      substituted). When the variable is unset, the URL is the default.
- [ ] Run the manual dead-port check from the spec once, and record in this ticket:
  - the single-source result;
  - the Cross-domain result;
  - that behavior returns to normal after unsetting the variable;
  - whether MCP connection failures are retried by the Specialist's `max_attempts` before UNAVAILABLE is reported.
- [ ] The `rate_limit` error kind is not exercised in v1. The dead port simulates a connection failure, not a 429.
- [ ] `ns validate` passes.
