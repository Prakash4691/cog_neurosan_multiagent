# Documentation Q&A

Answers developer questions and resolves error logs using only official documentation, and checks every answer
against that documentation before the user sees it.

## Language

### Questions

**Question**:
What the user asked, in their own words. It is the yardstick every answer is judged against, however many
Requeries happen.
_Avoid_: Query, prompt, request

**Error Log**:
Raw diagnostic output the user pastes in (stack trace, compiler or runtime error). It never leaves the
Coordinator as-is.
_Avoid_: Logs, trace

**Error Signature**:
The minimal, secret-free description of an Error Log: error type or code, message, library and version, and the
top relevant frames. It is the only form of an Error Log that Specialists see.
_Avoid_: Summary, cleaned log

**Out-of-scope Question**:
A Question that neither Microsoft Learn nor library documentation can ground. It is declined politely and is never
answered.
_Avoid_: Unsupported question, off-topic

**Cross-domain Question**:
A Question that needs both Microsoft documentation and library documentation, for example a React app calling
Azure Functions.

### Roles

**Coordinator**:
The single point of contact for the user. It routes the Question, passes work between the other roles and decides
when to stop.
_Avoid_: Main agent, orchestrator, router

**Specialist**:
A role that answers a Question from exactly one documentation source. There are two: the Microsoft Learn
Specialist and the Context7 Specialist. Coverage is decided by where the documentation lives, not by who makes
the product.
_Avoid_: Answerer, MCP agent, worker

**Microsoft Learn Specialist**:
Covers products documented on Microsoft Learn: Azure (including AKS), .NET and C#, Microsoft 365 and Graph,
Windows, Power Platform, SQL Server, Entra, and GitHub Actions used with those products.
_Avoid_: Microsoft agent

**Context7 Specialist**:
Covers library and framework documentation not on Microsoft Learn, including Microsoft-owned projects documented
elsewhere (TypeScript, VS Code extension APIs), plain GitHub Actions workflow syntax, general GitHub and plain
Kubernetes. A Question that could belong to either Specialist is treated as a Cross-domain Question.
_Avoid_: Library agent, open-source agent

**Verifier**:
The role that judges an Evidence Pack against the Question and returns a Verdict. It never answers or rewrites.
_Avoid_: Validator, checker, judge

**Requerier**:
The role that turns a failed Attempt into a Requery. It never answers.
_Avoid_: Rephraser, reformulator

### Answers and checks

**Evidence Pack**:
What a Specialist returns: the answer, its citations, and verbatim excerpts from the documentation retrieved in
the same Attempt.
_Avoid_: Response, result

**Excerpt**:
A verbatim quotation from documentation retrieved during the current Attempt. Only Excerpts count as grounding.
_Avoid_: Snippet, reference

**Check**:
One of three tests an Evidence Pack must pass: **Grounded** (every key claim is supported by an Excerpt),
**Relevant** (it matches the exact framework and version in the Question) and **Actionable** (for an Error Log, it
names a root cause and a fix tied to the Error Signature).

**Verdict**:
The Verifier's decision on one Evidence Pack: the failed Check, the reason, then VALID or INVALID, in that order.
_Avoid_: Score, rating, pass/fail

### The loop

**Attempt**:
One pass of a Question, or a Requery, through a Specialist and the Verifier. A Question gets at most three.
_Avoid_: Try, iteration, round

**Requery**:
A rewritten or decomposed form of the Question, made from a failed Verdict's reason, for the next Attempt.
_Avoid_: Retry, rephrase

**Unavailable Source**:
A documentation source that failed to respond during an Attempt (rate limit, timeout, error). It is reported to
the user and is not a Verdict, so it never triggers a Requery.
_Avoid_: Failed answer, invalid source

**Unverified Answer**:
The best Evidence Pack, returned with the last Verdict's reason when every Attempt has failed.
_Avoid_: Fallback, partial answer
