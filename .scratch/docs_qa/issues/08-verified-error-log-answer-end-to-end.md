# 08: Verified error-log answer end to end

Spec: `docs/spec/docs_qa.md` (Checks: Actionable).

**What to build:** a pasted error log now goes through the full loop. The developer gets a verified root cause and
fix tied to the Error Signature, or an Unverified Answer that says why.

**Blocked by:** 05, 06

**Status:** ready-for-agent

- [ ] An end-to-end fixture: a pasted log with a known, documented fix ends in a verified reply that names the root
      cause and the fix, with the verified-answer footer.
- [ ] The Relevant Check uses the library and version from the Error Signature even when the user stated no
      version. An end-to-end fixture shows this with a log naming a specific library version.
- [ ] The planted-secret fixture from 04 still passes with the loop in place.
