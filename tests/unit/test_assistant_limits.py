"""Checks that the deployed assistant and verifier networks set the limits in the spec's Limits table, without calling an
LLM. Expected values come from docs/spec/docs_qa.md (Limits)."""

import pytest
from neuro_san.internals.graph.persistence.agent_network_restorer import AgentNetworkRestorer

# Agents that don't set a limit themselves get the network's top-level value.
ASSISTANT = AgentNetworkRestorer(registry_dir="registries").restore("docs_qa/assistant.hocon").get_config()
VERIFIER = AgentNetworkRestorer(registry_dir="registries").restore("docs_qa/verifier.hocon").get_config()


def agent(network: dict, name: str) -> dict:
    return next(tool for tool in network["tools"] if tool["name"] == name)


def limit(network: dict, name: str, key: str):
    return agent(network, name).get(key, network.get(key))


@pytest.mark.parametrize(
    "network, name, max_steps, max_execution_seconds",
    [
        (ASSISTANT, "Coordinator", 240, 480),
        (ASSISTANT, "MicrosoftLearnSpecialist", 20, 90),
        (ASSISTANT, "Context7Specialist", 20, 90),
        (ASSISTANT, "Requerier", 10, 60),
        (VERIFIER, "Verifier", 10, 120),
    ],
    ids=lambda value: value if isinstance(value, str) else None,
)
def test_agent_step_and_time_limits(network: dict, name: str, max_steps: int, max_execution_seconds: int):
    assert limit(network, name, "max_steps") == max_steps
    assert limit(network, name, "max_execution_seconds") == max_execution_seconds


def test_coordinator_never_reruns_the_loop_on_a_retryable_llm_error():
    assert agent(ASSISTANT, "Coordinator")["max_attempts"] == 1


@pytest.mark.parametrize("name", ["MicrosoftLearnSpecialist", "Context7Specialist", "Requerier"])
def test_other_assistant_agents_keep_the_default_max_attempts(name: str):
    assert limit(ASSISTANT, name, "max_attempts") is None


def test_verifier_keeps_the_default_max_attempts():
    assert limit(VERIFIER, "Verifier", "max_attempts") is None


def test_assistant_sets_the_http_request_timeout_at_the_top_level():
    assert ASSISTANT["request_timeout_seconds"] == 540


def test_coordinator_calls_the_verifier_network_on_the_same_server():
    assert "/docs_qa/verifier" in agent(ASSISTANT, "Coordinator")["tools"]
