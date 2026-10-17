"""The verify-and-requery loop in the attempt_loop coded tool (ADR 0004), driven by scripted agent replies instead of
LLM calls. Rules come from docs/spec/docs_qa.md (The loop, Unavailable Source, Contracts)."""

import asyncio
import json

from coded_tools.docs_qa.assistant.attempt_loop import AttemptLoop
from coded_tools.docs_qa.assistant.attempt_loop import merge_packs
from coded_tools.docs_qa.assistant.attempt_loop import parse_json_object
from coded_tools.docs_qa.assistant.attempt_loop import run_attempts

MS = "MicrosoftLearnSpecialist"
C7 = "Context7Specialist"
VERIFIER = "/docs_qa/verifier"
REQUERIER = "Requerier"
QUESTION = "How do I enable CORS on an Azure Function App called from React?"


class ScriptedAgents:
    """Answers each agent call with the next scripted reply for that agent, and records the calls."""

    def __init__(self, replies: dict[str, list]):
        self.replies = replies
        self.calls: list[tuple[str, dict]] = []

    async def __call__(self, name: str, tool_args: dict) -> str:
        self.calls.append((name, tool_args))
        reply = self.replies[name].pop(0)
        if isinstance(reply, Exception):
            raise reply
        return reply if isinstance(reply, str) else json.dumps(reply)

    def called(self, name: str) -> list[dict]:
        return [tool_args for called_name, tool_args in self.calls if called_name == name]


def agents(**replies: list) -> ScriptedAgents:
    """Scripted replies by agent name. `verifier` stands for /docs_qa/verifier, which is not a Python name."""
    return ScriptedAgents({VERIFIER if name == "verifier" else name: list(r) for name, r in replies.items()})


def pack(answer: str = "Set allowed origins.", version: str = "not version-specific", urls=("https://a",)) -> dict:
    excerpts = [{"id": f"e{n}", "url": url, "quote": f"quote {n}"} for n, url in enumerate(urls, start=1)]
    return {
        "status": "OK",
        "version_covered": version,
        "excerpts": excerpts,
        "claims": [{"id": "c1", "text": answer, "excerpt_ids": [excerpt["id"] for excerpt in excerpts]}],
        "answer": answer,
    }


def verdict(*failed: str, reason: str = "reason") -> dict:
    return {"failed_checks": list(failed), "reason": reason, "verdict": "INVALID" if failed else "VALID"}


def requeries(*entries: tuple[str, str]) -> dict:
    return {"requeries": [{"question": question, "specialist": specialist} for question, specialist in entries]}


def run(scripted: ScriptedAgents, parts: list[dict] | None = None) -> dict:
    return asyncio.run(run_attempts(QUESTION, parts or [{"question": QUESTION, "specialist": MS}], scripted))


def test_a_valid_first_attempt_returns_a_verified_reply_with_numbered_sources():
    scripted = agents(MicrosoftLearnSpecialist=[pack(urls=("https://a", "https://b", "https://a"))],
                      verifier=[verdict()])

    result = run(scripted)

    assert result == {
        "outcome": "verified",
        "notes": [],
        "answer": "Set allowed origins.",
        "claims": [{"text": "Set allowed origins.", "sources": [1, 2]}],
        "version_covered": "not version-specific",
        "sources": "Sources:\n1. https://a (Microsoft Learn)\n2. https://b (Microsoft Learn)",
        "footer": "Verified against 3 documentation Excerpts.",
    }
    assert scripted.called(VERIFIER)[0]["question"] == QUESTION
    assert scripted.called(VERIFIER)[0]["evidence_pack"]["source"] == "ms_learn"
    assert not scripted.called(REQUERIER)


def test_sections_of_one_page_are_one_source():
    scripted = agents(MicrosoftLearnSpecialist=[pack(urls=("https://a/run-pipeline", "https://a/run-pipeline#run"))],
                      verifier=[verdict()])

    result = run(scripted)

    assert result["claims"][0]["sources"] == [1]
    assert result["sources"] == "Sources:\n1. https://a/run-pipeline (Microsoft Learn)"


def slow(scripted: ScriptedAgents, name: str):
    """Calls the scripted agents, but `name` never answers in time."""

    async def call_agent(called_name: str, tool_args: dict) -> str:
        if called_name == name:
            await asyncio.sleep(10)
        return await scripted(called_name, tool_args)

    return call_agent


def test_a_loop_out_of_time_returns_its_best_attempt_as_unverified():
    scripted = agents(MicrosoftLearnSpecialist=[pack("one")], verifier=[verdict("ACTIONABLE", reason="No steps.")],
                      Requerier=[requeries(("Again?", MS))])
    parts = [{"question": QUESTION, "specialist": MS}]

    result = asyncio.run(run_attempts(QUESTION, parts, slow(scripted, REQUERIER), loop_seconds=0.1))

    assert result["outcome"] == "not_verified"
    assert result["answer"] == "one"
    assert result["not_verified_reason"] == "No steps."
    assert result["notes"] == ["I ran out of time to look this up again, so this is the best answer I found."]


def test_a_loop_out_of_time_before_any_attempt_says_so():
    scripted = agents(MicrosoftLearnSpecialist=[pack()])
    parts = [{"question": QUESTION, "specialist": MS}]

    result = asyncio.run(run_attempts(QUESTION, parts, slow(scripted, MS), loop_seconds=0.1))

    assert result == {
        "outcome": "unavailable",
        "reply": "Sorry, I couldn't finish looking this up in time. Please try again.",
    }


def test_a_cross_domain_question_merges_both_packs_with_unique_ids_and_sources():
    scripted = agents(MicrosoftLearnSpecialist=[pack("Enable CORS.", urls=("https://learn",))],
                      Context7Specialist=[pack("Call fetch.", "React 19.1", urls=("https://react",))],
                      verifier=[verdict()])
    parts = [{"question": "Enable CORS on a Function App?", "specialist": MS},
             {"question": "Call an API from React?", "specialist": C7}]

    result = run(scripted, parts)

    merged = scripted.called(VERIFIER)[0]["evidence_pack"]
    assert [claim["id"] for claim in merged["claims"]] == ["p1-c1", "p2-c1"]
    assert [claim["excerpt_ids"] for claim in merged["claims"]] == [["p1-e1"], ["p2-e1"]]
    assert [excerpt["source"] for excerpt in merged["excerpts"]] == ["ms_learn", "context7"]
    assert merged["version_covered"] == "Microsoft Learn: not version-specific; Context7: React 19.1"
    assert result["sources"] == "Sources:\n1. https://learn (Microsoft Learn)\n2. https://react (Context7)"
    assert result["claims"] == [{"text": "Enable CORS.", "sources": [1]}, {"text": "Call fetch.", "sources": [2]}]


def test_merging_a_pack_without_a_version_leaves_the_version_unstated():
    unstated = {**pack(), "source": "context7", "version_covered": ""}
    assert merge_packs([{**pack(), "source": "ms_learn"}, unstated])["version_covered"] == ""


def test_merging_packs_from_one_source_lists_each_version_once_without_a_source_name():
    packs = [{**pack(version=version), "source": "ms_learn"} for version in ("Azure.Core 1.44", "Azure.Core 1.44", ".NET 8")]
    assert merge_packs(packs)["version_covered"] == "Azure.Core 1.44; .NET 8"


def test_a_pack_without_excerpts_fails_grounded_without_a_verifier_call():
    empty = {**pack(), "claims": [], "excerpts": [], "answer": "The documentation does not say."}
    scripted = agents(MicrosoftLearnSpecialist=[empty, pack()], verifier=[verdict()],
                      Requerier=[requeries(("Rephrased?", MS))])

    result = run(scripted)

    assert result["outcome"] == "verified"
    assert len(scripted.called(VERIFIER)) == 1
    assert "GROUNDED failed: the pack has no excerpts" in scripted.called(REQUERIER)[0]["reason"]
    assert scripted.called(MS)[1] == {"question": "Rephrased?"}


def test_a_claim_citing_a_missing_excerpt_and_an_unstated_version_fail_without_a_verifier_call():
    broken = pack(version="")
    broken["claims"][0]["excerpt_ids"] = ["e9"]
    scripted = agents(MicrosoftLearnSpecialist=[broken], Requerier=[requeries()])

    result = run(scripted)

    assert not scripted.called(VERIFIER)
    assert result["outcome"] == "not_verified"
    assert "claim c1 cites an excerpt id that is not in the pack" in result["not_verified_reason"]
    assert "RELEVANT failed" in result["not_verified_reason"]


def test_the_loop_stops_after_three_attempts_and_picks_the_unverified_answer():
    # Attempt 2 passes GROUNDED, so it beats Attempt 3, which fails fewer Checks but fails GROUNDED.
    scripted = agents(
        MicrosoftLearnSpecialist=[pack("one"), pack("two"), pack("three")],
        verifier=[verdict("GROUNDED", "RELEVANT"), verdict("RELEVANT", "ACTIONABLE", reason="wrong version"),
                  verdict("GROUNDED")],
        Requerier=[requeries(("Again?", MS)), requeries(("Once more?", MS))],
    )

    result = run(scripted)

    assert len(scripted.called(MS)) == 3
    assert len(scripted.called(REQUERIER)) == 2
    assert result["outcome"] == "not_verified"
    assert result["answer"] == "two"
    assert result["not_verified_reason"] == "wrong version"
    assert result["footer"] == ""


def test_tied_unverified_attempts_pick_the_later_one():
    scripted = agents(MicrosoftLearnSpecialist=[pack("one"), pack("two")],
                      verifier=[verdict("RELEVANT"), verdict("ACTIONABLE")],
                      Requerier=[requeries(("Again?", MS)), requeries()])

    assert run(scripted)["answer"] == "two"


def test_every_requery_from_one_requerier_output_is_one_attempt_and_the_verifier_gets_the_original_question():
    scripted = agents(
        MicrosoftLearnSpecialist=[pack("one"), pack("two")],
        Context7Specialist=[pack("three", "React 19.1", urls=("https://react",))],
        verifier=[verdict("GROUNDED"), verdict()],
        Requerier=[requeries(("Part A?", MS), ("Part B?", C7), ("Part C?", MS))],
    )

    result = run(scripted)

    # At most 2 Requeries are used.
    assert [call["question"] for call in scripted.called(MS)] == [QUESTION, "Part A?"]
    assert [call["question"] for call in scripted.called(C7)] == ["Part B?"]
    assert [call["question"] for call in scripted.called(VERIFIER)] == [QUESTION, QUESTION]
    assert result["outcome"] == "verified"


def test_the_requerier_gets_the_failed_pack_without_quotes():
    scripted = agents(MicrosoftLearnSpecialist=[pack()], verifier=[verdict("ACTIONABLE", reason="no steps")],
                      Requerier=[requeries()])

    run(scripted)

    sent = scripted.called(REQUERIER)[0]
    assert sent["question"] == QUESTION
    assert sent["reason"] == "no steps"
    assert sent["evidence_pack"]["excerpts"] == [{"id": "e1", "url": "https://a"}]
    assert sent["evidence_pack"]["claims"] == pack()["claims"]


def test_a_requerier_error_or_empty_list_ends_the_loop_with_the_unverified_answer():
    for requerier_reply in (RuntimeError("boom"), "not json", requeries(), requeries(("Q?", "SomeoneElse"))):
        scripted = agents(MicrosoftLearnSpecialist=[pack()], verifier=[verdict("RELEVANT")],
                          Requerier=[requerier_reply])
        result = run(scripted)
        assert result["outcome"] == "not_verified"
        assert len(scripted.called(MS)) == 1


def test_a_missing_verdict_counts_as_invalid_on_every_check():
    scripted = agents(MicrosoftLearnSpecialist=[pack()], verifier=["Agent timed out"], Requerier=[requeries()])

    result = run(scripted)

    assert result["outcome"] == "not_verified"
    assert result["not_verified_reason"] == "The Verifier did not return a Verdict."


def test_a_valid_verdict_that_lists_a_failed_check_is_invalid():
    scripted = agents(MicrosoftLearnSpecialist=[pack()],
                      verifier=[{"failed_checks": ["RELEVANT"], "reason": "r", "verdict": "VALID"}],
                      Requerier=[requeries()])

    assert run(scripted)["outcome"] == "not_verified"


def test_a_single_source_down_on_attempt_one_gets_the_unavailable_reply():
    scripted = agents(Context7Specialist=[{"status": "UNAVAILABLE", "error_kind": "rate_limit"}])

    result = run(scripted, [{"question": QUESTION, "specialist": C7}])

    assert result == {
        "outcome": "unavailable",
        "reply": "Sorry, I can't answer this right now: Context7 is unavailable. Please try again later.",
    }
    assert not scripted.called(VERIFIER)


def test_both_sources_down_are_named_together():
    scripted = agents(MicrosoftLearnSpecialist=[RuntimeError("down")], Context7Specialist=["Agent timed out: 90s"])
    parts = [{"question": QUESTION, "specialist": MS}, {"question": QUESTION, "specialist": C7}]

    result = run(scripted, parts)

    assert result["reply"] == ("Sorry, I can't answer this right now: Microsoft Learn and Context7 are unavailable. "
                               "Please try again later.")


def test_an_error_body_from_neuro_san_counts_as_unavailable():
    scripted = agents(MicrosoftLearnSpecialist=['{"error": "LLM provider error", "tool": "MicrosoftLearnSpecialist"}'])

    assert run(scripted)["outcome"] == "unavailable"


def test_one_source_down_in_a_cross_domain_question_is_listed_and_its_requeries_are_dropped():
    scripted = agents(
        MicrosoftLearnSpecialist=[pack("Enable CORS."), pack("Enable CORS in the portal.")],
        Context7Specialist=["Agent timed out: max_execution_seconds=90s exceeded."],
        verifier=[verdict("ACTIONABLE"), verdict()],
        Requerier=[requeries(("CORS steps?", MS), ("React fetch?", C7))],
    )
    parts = [{"question": "Enable CORS on a Function App?", "specialist": MS},
             {"question": "Call an API from React?", "specialist": C7}]

    result = run(scripted, parts)

    expected_parts = [{"part": "Call an API from React?", "source": "context7", "error_kind": "timeout"}]
    assert [call["evidence_pack"]["unavailable_parts"] for call in scripted.called(VERIFIER)] == [expected_parts] * 2
    assert len(scripted.called(C7)) == 1
    assert result["outcome"] == "verified"
    assert result["notes"] == ["Not answered: Call an API from React. Context7 is unavailable. Please try again later."]


def test_a_source_down_on_a_later_attempt_returns_the_earlier_unverified_answer():
    scripted = agents(
        MicrosoftLearnSpecialist=[pack("one"), {"status": "UNAVAILABLE", "error_kind": "error"}],
        verifier=[verdict("ACTIONABLE")],
        Requerier=[requeries(("Again?", MS))],
    )

    result = run(scripted)

    assert result["outcome"] == "not_verified"
    assert result["answer"] == "one"
    assert result["notes"] == [
        "Microsoft Learn became unavailable, so I could not check this answer again. Please try again later."
    ]


def test_a_specialist_reply_in_a_json_fence_is_parsed():
    fenced = "Here is the pack:\n```json\n" + json.dumps(pack()) + "\n```"
    scripted = agents(MicrosoftLearnSpecialist=[fenced], verifier=[verdict()])

    assert run(scripted)["outcome"] == "verified"


def test_parse_json_object_skips_braces_that_are_not_json():
    assert parse_json_object('Use {braces} then {"a": 1}') == {"a": 1}
    assert parse_json_object("no json") is None


def test_bad_arguments_get_an_error_message_without_calling_any_agent():
    tool = AttemptLoop.__new__(AttemptLoop)  # async_invoke checks arguments before it needs neuro-san's state.

    def invoke(args: dict) -> str:
        return asyncio.run(tool.async_invoke(args, {}))

    assert invoke({"parts": [{"question": "Q?", "specialist": MS}]}).startswith("Error: question is empty")
    assert invoke({"question": "Q?"}).startswith("Error: parts is empty")
    assert invoke({"question": "Q?", "parts": [{"question": "Q?", "specialist": "X"}]}).startswith("Error:")
