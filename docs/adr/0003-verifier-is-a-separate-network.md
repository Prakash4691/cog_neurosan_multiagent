# The Verifier is its own agent network, called by the Coordinator as an external agent

neuro-san integration test fixtures talk to a network's Front Man, so an agent inside a network cannot be tested on
its own. To test the Verifier against a golden set of known-valid and known-invalid (Question, Evidence Pack) pairs,
it is a separate network that the hub calls through a same-server `/name` reference. Its Front Man declares
`question` and `evidence_pack` as explicit `function.parameters`. Without them, neuro-san gives an external
agent one synthesized `inquiry` string parameter (`BaseToolFactory.DEFAULT_EXTERNAL_PARAMETERS`), and the two inputs
would be merged into free text.

## Consequences

- No `sly_data` reaches an external agent unless `allow.to_downstream.sly_data` permits it. Everything the Verifier
  needs must be in its tool-call arguments.
