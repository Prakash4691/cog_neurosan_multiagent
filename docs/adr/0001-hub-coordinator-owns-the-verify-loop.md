# The Coordinator owns the verify-and-requery loop (hub, not a cycle)

The loop itself now runs in the Coordinator's `attempt_loop` coded tool (ADR 0004). The hub stays.

The first design was a chain: main agent → Verifier → Requerier → main agent. neuro-san allows cycles, but it runs a
cycle as nested calls, so every Requery adds a level, the final answer has to pass back up through every caller, and
no single agent knows how many Attempts have run. We use a hub instead. The Coordinator calls the Specialists, the
Verifier and the Requerier in turn, and none of them calls another agent. The Coordinator keeps the original Question,
counts Attempts and decides when to stop.

## Consequences

- The Attempt cap (3) is enforced by the Coordinator's instructions, not by code. `max_steps` and
  `max_execution_seconds` are the hard backstop. If the model is seen to overrun the cap, move the count into
  `sly_data` with a small coded tool.
