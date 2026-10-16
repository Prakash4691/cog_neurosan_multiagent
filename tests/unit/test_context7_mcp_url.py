"""Checks the optional CONTEXT7_MCP_URL override of the Context7 Specialist's server URL, without calling an LLM.
Spec: docs/spec/docs_qa.md (MCP servers, Manual check: Unavailable Source)."""

import pytest
from neuro_san.internals.graph.persistence.agent_network_restorer import AgentNetworkRestorer
from neuro_san.internals.run_context.langchain.mcp.mcp_servers_info_restorer import McpServersInfoRestorer

DEFAULT_CONTEXT7_URL = "https://mcp.context7.com/mcp"
DEAD_PORT_URL = "http://localhost:9/mcp"


def context7_specialist_tools() -> list:
    # Restored on each call: the override is read from the environment when the HOCON is parsed.
    network = AgentNetworkRestorer(registry_dir="registries").restore("docs_qa/assistant.hocon").get_config()
    return next(tool for tool in network["tools"] if tool["name"] == "Context7Specialist")["tools"]


def test_context7_url_is_the_default_when_the_variable_is_unset(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.delenv("CONTEXT7_MCP_URL", raising=False)
    assert context7_specialist_tools() == [DEFAULT_CONTEXT7_URL]


def test_context7_url_comes_from_the_variable_when_it_is_set(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("CONTEXT7_MCP_URL", DEAD_PORT_URL)
    assert context7_specialist_tools() == [DEAD_PORT_URL]


def test_default_context7_url_matches_its_key_in_the_mcp_server_config():
    # A mismatch would silently stop the tool allow list from applying.
    assert DEFAULT_CONTEXT7_URL in McpServersInfoRestorer().restore("mcp/mcp_info.hocon")
