# The verify loop runs in a coded tool, not in the Coordinator's prompt

Steps 4 to 7 of the Coordinator's instructions were fixed rules written as prose: count Attempts, call each role
once, handle an Unavailable Source, merge Evidence Packs, choose the Unverified Answer, number the sources. They were
about half of its prompt, which went out again with every Coordinator LLM call, and the model broke them in manual
testing (issues 11, 12 and 14). Every Evidence Pack also passed through the Coordinator's LLM. The model wrote each
pack out again for the Verifier and the Requerier, and that slow output caused the timeouts in issue 14.

The loop is now the `attempt_loop` coded tool. It subclasses `BranchActivation` to get `use_tool()`, which calls
agents in the network and same-server networks from Python, as `write_all_instructions` does in the designer
networks. The Coordinator still makes the judgment calls: it writes the standalone Question, gets the Error
Signature, chooses the Specialists and parts or declines, and writes the reply. It calls `attempt_loop` once with
the Question and its parts. The tool returns the parts of the reply that need no LLM: the outcome, the answer and
claims with source numbers, the version, the Sources list, the footer and the fixed notes. The quotes never reach
the Coordinator.

This keeps ADR 0001's hub. One place owns the original Question and the Attempt count, and no LLM agent calls another.
That place is now code. The Attempt cap is enforced by code, as ADR 0001 planned if the model overran it. The tool
needs no `sly_data` because the whole loop runs inside one tool call.

## Consequences

- The Verifier's mechanical checks run in code before it is called: no excerpts, no claims, a claim citing no
  excerpt or an unknown one, and no stated version. A pack that fails one is INVALID without a Verifier call. That
  Verdict lists only the mechanical failures, so when it is compared in choosing the Unverified Answer, it can count
  fewer failed Checks than a full Verifier run would.
- Specialists in one Attempt run concurrently.
- The Requerier gets the failed pack without its quotes. It needs the claims, the version and the unavailable parts,
  not the documentation text.
- `use_tool()` is marked experimental in neuro-san, and its docstring says it does not report history correctly yet.
  In practice the nsflow graph shows `attempt_loop` connected to the agents it calls (they are in its `args.tools`),
  and its live view lights up each Specialist and Verifier call during a run (checked 2026-10-16).
- The loop rules are unit-tested with scripted agent replies (`tests/unit/test_attempt_loop.py`), with no LLM.
