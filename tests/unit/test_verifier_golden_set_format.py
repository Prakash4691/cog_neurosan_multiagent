"""Checks the golden-set fixture format without calling an LLM, so a hand-edited case can't drift from what a real
tool call sends the Verifier."""

import json
from pathlib import Path

import pytest
from pyhocon import ConfigFactory

GOLDEN_SET_DIR = Path(__file__).resolve().parent.parent / "fixtures" / "docs_qa" / "verifier"
GOLDEN_SET = sorted(GOLDEN_SET_DIR.glob("*.hocon"))

CHECKS = {"GROUNDED", "RELEVANT", "ACTIONABLE"}

# neuro-san sends an external agent its tool-call arguments as "```json\n" + json.dumps(arguments) + "```".
FENCE_START = "```json\n"
FENCE_END = "```"


def test_golden_set_covers_every_required_case():
    names = {path.stem for path in GOLDEN_SET}
    required = {
        "invalid_grounded",
        "invalid_relevant_wrong_version",
        "invalid_relevant_no_version_stated",
        "invalid_actionable_no_fix",
        "valid",
        "valid_no_version_stated",
        "valid_cross_domain_unavailable_parts",
    }
    assert required <= names


@pytest.mark.parametrize("fixture_path", GOLDEN_SET, ids=lambda path: path.stem)
def test_golden_case_format(fixture_path: Path):
    case = ConfigFactory.parse_file(str(fixture_path))
    assert case["agent"] == "docs_qa/verifier"
    assert len(case["interactions"]) == 1
    interaction = case["interactions"][0]

    text = interaction["text"]
    assert text.startswith(FENCE_START) and text.endswith(FENCE_END)
    arguments = json.loads(text[len(FENCE_START):-len(FENCE_END)])
    assert set(arguments) == {"question", "evidence_pack"}
    assert isinstance(arguments["question"], str) and arguments["question"]

    pack = arguments["evidence_pack"]
    assert isinstance(pack["answer"], str)
    assert "version_covered" in pack
    for claim in pack["claims"]:
        assert {"id", "text", "excerpt_ids"} <= set(claim)
    for excerpt in pack["excerpts"]:
        assert {"id", "url", "quote"} <= set(excerpt)
    for part in pack.get("unavailable_parts", []):
        assert set(part) == {"part", "source", "error_kind"}

    # keywords are the Checks that must fail, not_keywords the Checks that must pass. A Check in neither is one whose
    # outcome is arguable for this case, so it is not asserted.
    structure = interaction["response"]["structure"]
    failed = set(structure["failed_checks"].get("keywords", []))
    passed = set(structure["failed_checks"].get("not_keywords", []))
    assert failed | passed <= CHECKS and not failed & passed

    verdict = structure["verdict"]
    if failed:
        assert verdict["keywords"] == ["INVALID"]
    else:
        # A VALID Verdict means every Check passed, so nothing is arguable. "VALID" is a substring of "INVALID", so
        # a VALID case must also rule INVALID out.
        assert passed == CHECKS
        assert verdict["keywords"] == ["VALID"] and verdict["not_keywords"] == ["INVALID"]
