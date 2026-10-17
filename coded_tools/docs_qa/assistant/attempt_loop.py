import asyncio
import json
import logging
from collections.abc import Awaitable
from collections.abc import Callable
from collections.abc import Iterable
from typing import Any

from neuro_san.interfaces.coded_tool import CodedTool
from neuro_san.internals.graph.activations.branch_activation import BranchActivation

MAX_ATTEMPTS = 3
MAX_REQUERIES = 2
CHECKS = ("GROUNDED", "RELEVANT", "ACTIONABLE")

SPECIALIST_SOURCES = {"MicrosoftLearnSpecialist": "ms_learn", "Context7Specialist": "context7"}
SOURCE_NAMES = {"ms_learn": "Microsoft Learn", "context7": "Context7"}
ERROR_KINDS = ("rate_limit", "timeout", "error")

# The loop runs inside the Coordinator's 480 seconds. Stopping it at 360 leaves the Coordinator time for its own LLM
# rounds, so a slow run returns its best Attempt instead of no reply at all (issue 16).
LOOP_SECONDS = 360
OUT_OF_TIME_NOTE = "I ran out of time to look this up again, so this is the best answer I found."
OUT_OF_TIME_REPLY = "Sorry, I couldn't finish looking this up in time. Please try again."

VERIFIER = "/docs_qa/verifier"
REQUERIER = "Requerier"

NO_VERDICT = {
    "failed_checks": list(CHECKS),
    "reason": "The Verifier did not return a Verdict.",
    "verdict": "INVALID",
}

# Calls an agent by name with tool arguments and returns its reply text.
AgentCall = Callable[[str, dict[str, Any]], Awaitable[str]]


class AttemptLoop(BranchActivation, CodedTool):
    """Runs the verify-and-requery loop for one Question (ADR 0004): asks the Specialists, merges their Evidence
    Packs, has the Verifier judge each Attempt, asks the Requerier for Requeries, and picks the Unverified Answer.
    It returns the parts of the reply that need no LLM, so Evidence Packs never pass through the Coordinator's LLM.

    BranchActivation gives a CodedTool use_tool(), which calls other agents in this network or on the same server.
    """

    async def async_invoke(self, args: dict[str, Any], sly_data: dict[str, Any]) -> dict[str, Any] | str:
        question: str = (args.get("question") or "").strip()
        parts: list[Any] = args.get("parts") or []
        error = _check_args(question, parts)
        if error:
            return error

        async def call_agent(name: str, tool_args: dict[str, Any]) -> str:
            return await self.use_tool(name, tool_args, sly_data)

        return await run_attempts(question, parts, call_agent)


def _check_args(question: str, parts: list[Any]) -> str:
    if not question:
        return "Error: question is empty. Pass the standalone Question."
    if not parts:
        return "Error: parts is empty. Pass one entry per Specialist to call."
    for part in parts:
        if not isinstance(part, dict) or not (part.get("question") or "").strip():
            return "Error: each entry in parts needs a question."
        if part.get("specialist") not in SPECIALIST_SOURCES:
            return "Error: each entry in parts needs a specialist: MicrosoftLearnSpecialist or Context7Specialist."
    return ""


async def run_attempts(
    question: str, parts: list[dict[str, Any]], call_agent: AgentCall, loop_seconds: float = LOOP_SECONDS
) -> dict[str, Any]:
    attempts: list[tuple[dict[str, Any], dict[str, Any]]] = []
    try:
        async with asyncio.timeout(loop_seconds):
            return await _run_until_done(question, parts, call_agent, attempts)
    except TimeoutError:
        logging.warning("The loop ran out of time after %d Attempts.", len(attempts))
    if not attempts:
        return {"outcome": "unavailable", "reply": OUT_OF_TIME_REPLY}
    return reply(*pick_unverified(attempts), verified=False, extra_notes=[OUT_OF_TIME_NOTE])


async def _run_until_done(
    question: str,
    parts: list[dict[str, Any]],
    call_agent: AgentCall,
    attempts: list[tuple[dict[str, Any], dict[str, Any]]],
) -> dict[str, Any]:
    """The loop itself. It adds each judged Attempt to `attempts`, so run_attempts can still pick one if time runs
    out."""
    unavailable_parts: list[dict[str, str]] = []
    unavailable_specialists: set[str] = set()
    queries = parts

    for number in range(1, MAX_ATTEMPTS + 1):
        packs = await asyncio.gather(*(ask_specialist(call_agent, query) for query in queries))
        ok_packs = [pack for pack in packs if pack["status"] == "OK"]
        down = [(query, pack) for query, pack in zip(queries, packs) if pack["status"] != "OK"]

        if down and number > 1:
            # A source that goes down mid-loop ends it: this Attempt's packs are not used (spec, Unavailable Source).
            became_unavailable = _source_names(SPECIALIST_SOURCES[query["specialist"]] for query, _ in down)
            note = (
                f"{became_unavailable} became unavailable, so I could not check this answer again. "
                "Please try again later."
            )
            return reply(*pick_unverified(attempts), verified=False, extra_notes=[note])
        if not ok_packs:
            return unavailable_reply(SPECIALIST_SOURCES[query["specialist"]] for query, _ in down)
        for query, pack in down:
            unavailable_specialists.add(query["specialist"])
            unavailable_parts.append(
                {
                    "part": query["question"],
                    "source": SPECIALIST_SOURCES[query["specialist"]],
                    "error_kind": pack["error_kind"],
                }
            )

        pack = merge_packs(ok_packs) if len(ok_packs) > 1 else ok_packs[0]
        if unavailable_parts:
            pack["unavailable_parts"] = list(unavailable_parts)

        verdict = precheck(pack) or await ask_verifier(call_agent, question, pack)
        attempts.append((pack, verdict))
        logging.info("Attempt %d: %s %s", number, verdict["verdict"], verdict["failed_checks"])
        if verdict["verdict"] == "VALID":
            return reply(pack, verdict, verified=True)
        if number == MAX_ATTEMPTS:
            break

        requeries = await ask_requerier(call_agent, question, pack, verdict["reason"])
        queries = [requery for requery in requeries if requery["specialist"] not in unavailable_specialists]
        if not queries:
            break

    return reply(*pick_unverified(attempts), verified=False)


async def ask_specialist(call_agent: AgentCall, query: dict[str, Any]) -> dict[str, Any]:
    specialist: str = query["specialist"]
    try:
        text = await call_agent(specialist, {"question": query["question"]})
    except Exception as exception:  # pylint: disable=broad-exception-caught
        # Any failure to get a pack means the source is unavailable for this Question: there is no retry.
        logging.warning("%s failed: %r", specialist, exception)
        kind = "timeout" if isinstance(exception, (TimeoutError, asyncio.TimeoutError)) else "error"
        return {"status": "UNAVAILABLE", "error_kind": kind}

    pack = parse_json_object(text)
    # neuro-san replies "Agent timed out: max_execution_seconds=..." for an agent it cancelled, and may report other
    # failures as an {"error": ...} body.
    if pack is None or ("error" in pack and "claims" not in pack):
        logging.warning("%s returned no Evidence Pack: %.200s", specialist, text)
        return {"status": "UNAVAILABLE", "error_kind": "timeout" if "timed out" in text.lower() else "error"}
    if str(pack.get("status", "OK")).upper() == "UNAVAILABLE":
        kind = pack.get("error_kind")
        return {"status": "UNAVAILABLE", "error_kind": kind if kind in ERROR_KINDS else "error"}

    return {
        "source": SPECIALIST_SOURCES[specialist],
        "status": "OK",
        "version_covered": str(pack.get("version_covered") or "").strip(),
        "answer": str(pack.get("answer") or ""),
        "claims": _list_of_dicts(pack.get("claims")),
        "excerpts": _list_of_dicts(pack.get("excerpts")),
    }


async def ask_verifier(call_agent: AgentCall, question: str, pack: dict[str, Any]) -> dict[str, Any]:
    try:
        text = await call_agent(VERIFIER, {"question": question, "evidence_pack": pack})
    except Exception as exception:  # pylint: disable=broad-exception-caught
        logging.warning("The Verifier failed: %r", exception)
        return dict(NO_VERDICT)

    verdict = parse_json_object(text)
    if verdict is None or not isinstance(verdict.get("failed_checks"), list):
        logging.warning("The Verifier returned no Verdict: %.200s", text)
        return dict(NO_VERDICT)
    failed_checks = [check for check in CHECKS if check in verdict["failed_checks"]]
    # VALID only when the Verifier says so and lists no failed Check.
    valid = not failed_checks and str(verdict.get("verdict", "")).upper() == "VALID"
    return {
        "failed_checks": failed_checks,
        "reason": str(verdict.get("reason") or ""),
        "verdict": "VALID" if valid else "INVALID",
    }


async def ask_requerier(
    call_agent: AgentCall, question: str, pack: dict[str, Any], reason: str
) -> list[dict[str, str]]:
    # The Requerier needs the claims, versions and unavailable parts, not the quotes. Leaving them out keeps its
    # input small: it timed out on large packs (issues 09 and 14).
    slim_pack = {**pack, "excerpts": [{"id": e.get("id"), "url": e.get("url")} for e in pack["excerpts"]]}
    try:
        text = await call_agent(REQUERIER, {"question": question, "evidence_pack": slim_pack, "reason": reason})
    except Exception as exception:  # pylint: disable=broad-exception-caught
        logging.warning("The Requerier failed: %r", exception)
        return []

    output = parse_json_object(text) or {}
    requeries = []
    for requery in _list_of_dicts(output.get("requeries")):
        requery_question = str(requery.get("question") or "").strip()
        if requery_question and requery.get("specialist") in SPECIALIST_SOURCES:
            requeries.append({"question": requery_question, "specialist": requery["specialist"]})
    return requeries[:MAX_REQUERIES]


def precheck(pack: dict[str, Any]) -> dict[str, Any] | None:
    """The Verifier's mechanical checks. A pack that fails one is INVALID without a Verifier call."""
    grounded: list[str] = []
    excerpt_ids = {excerpt.get("id") for excerpt in pack["excerpts"]}
    if not pack["excerpts"]:
        grounded.append("the pack has no excerpts, so no documentation backs the answer")
    elif not pack["claims"]:
        grounded.append("the pack has no claims, so nothing in the answer is tied to an excerpt")
    for claim in pack["claims"]:
        cited = claim.get("excerpt_ids") or []
        if not cited:
            grounded.append(f"claim {claim.get('id')} cites no excerpt")
        elif any(excerpt_id not in excerpt_ids for excerpt_id in cited):
            grounded.append(f"claim {claim.get('id')} cites an excerpt id that is not in the pack")

    reasons = []
    failed_checks = []
    if grounded:
        failed_checks.append("GROUNDED")
        reasons.append("GROUNDED failed: " + "; ".join(grounded) + ".")
    if not pack["version_covered"]:
        failed_checks.append("RELEVANT")
        reasons.append("RELEVANT failed: the pack does not say which version its documentation covers.")
    if not failed_checks:
        return None
    return {"failed_checks": failed_checks, "reason": " ".join(reasons), "verdict": "INVALID"}


def merge_packs(packs: list[dict[str, Any]]) -> dict[str, Any]:
    """Keeps every claim and excerpt, tags each with its pack's source, and prefixes ids p1-, p2-... so they stay
    unique."""
    claims = []
    excerpts = []
    for number, pack in enumerate(packs, start=1):
        prefix = f"p{number}-"
        for claim in pack["claims"]:
            claims.append(
                {
                    **claim,
                    "id": f"{prefix}{claim.get('id')}",
                    "excerpt_ids": [f"{prefix}{excerpt_id}" for excerpt_id in claim.get("excerpt_ids") or []],
                    "source": pack["source"],
                }
            )
        for excerpt in pack["excerpts"]:
            excerpts.append({**excerpt, "id": f"{prefix}{excerpt.get('id')}", "source": pack["source"]})

    # One pack that does not state its version leaves the merged version unstated, so RELEVANT fails. Source names
    # are added only when the packs come from different sources, such as two Requeries for one Specialist.
    labelled = len({pack["source"] for pack in packs}) > 1
    versions = []
    for pack in packs:
        version = f"{SOURCE_NAMES[pack['source']]}: {pack['version_covered']}" if labelled else pack["version_covered"]
        if version not in versions:
            versions.append(version)
    stated = all(pack["version_covered"] for pack in packs)
    return {
        "status": "OK",
        "version_covered": "; ".join(versions) if stated else "",
        "answer": "\n\n".join(pack["answer"] for pack in packs if pack["answer"]),
        "claims": claims,
        "excerpts": excerpts,
    }


def pick_unverified(
    attempts: list[tuple[dict[str, Any], dict[str, Any]]],
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Passing GROUNDED beats failing it, then fewer failed Checks win, then the later Attempt wins."""
    best = min(
        range(len(attempts)),
        key=lambda index: (
            "GROUNDED" in attempts[index][1]["failed_checks"],
            len(attempts[index][1]["failed_checks"]),
            -index,
        ),
    )
    return attempts[best]


def reply(
    pack: dict[str, Any], verdict: dict[str, Any], *, verified: bool, extra_notes: list[str] | None = None
) -> dict[str, Any]:
    """The reply's parts. The Coordinator writes the answer and the "Not verified" sentences, and copies the rest."""
    excerpts = {excerpt.get("id"): excerpt for excerpt in pack["excerpts"]}
    url_numbers: dict[str, int] = {}
    url_sources: dict[str, str] = {}
    claims = []
    for claim in pack["claims"]:
        numbers = []
        for excerpt_id in claim.get("excerpt_ids") or []:
            excerpt = excerpts.get(excerpt_id)
            if not excerpt or not excerpt.get("url"):
                continue
            # Search results link to a section (page#anchor) and fetched pages don't: both are one source.
            url = excerpt["url"].split("#", 1)[0]
            if url not in url_numbers:
                url_numbers[url] = len(url_numbers) + 1
                url_sources[url] = excerpt.get("source") or pack.get("source")
            if url_numbers[url] not in numbers:
                numbers.append(url_numbers[url])
        claims.append({"text": claim.get("text", ""), "sources": numbers})

    notes = list(extra_notes or [])
    for part in pack.get("unavailable_parts", []):
        source_name = SOURCE_NAMES[part["source"]]
        notes.append(f"Not answered: {part['part'].rstrip('.?')}. {source_name} is unavailable. Please try again later.")

    sources = ""
    if url_numbers:
        lines = [f"{number}. {url} ({SOURCE_NAMES[url_sources[url]]})" for url, number in url_numbers.items()]
        sources = "Sources:\n" + "\n".join(lines)

    result: dict[str, Any] = {"outcome": "verified" if verified else "not_verified"}
    if not verified:
        result["not_verified_reason"] = verdict["reason"]
    result.update(
        {
            "notes": notes,
            "answer": pack["answer"],
            "claims": claims,
            "version_covered": pack["version_covered"] or "not stated",
            "sources": sources,
            "footer": f"Verified against {len(pack['excerpts'])} documentation Excerpts." if verified else "",
        }
    )
    return result


def unavailable_reply(sources: Iterable[str]) -> dict[str, Any]:
    names = _source_names(sources)
    verb = "are" if " and " in names else "is"
    return {
        "outcome": "unavailable",
        "reply": f"Sorry, I can't answer this right now: {names} {verb} unavailable. Please try again later.",
    }


def _source_names(sources: Iterable[str]) -> str:
    """Names the sources in a fixed order, such as "Microsoft Learn and Context7"."""
    wanted = set(sources)
    return " and ".join(name for source, name in SOURCE_NAMES.items() if source in wanted)


def parse_json_object(text: Any) -> dict[str, Any] | None:
    """The first JSON object in an agent's reply, which may wrap it in a ```json fence or a sentence."""
    if not isinstance(text, str):
        return None
    decoder = json.JSONDecoder()
    for index, char in enumerate(text):
        if char != "{":
            continue
        try:
            value, _ = decoder.raw_decode(text, index)
        except json.JSONDecodeError:
            continue
        return value
    return None


def _list_of_dicts(value: Any) -> list[dict[str, Any]]:
    return [item for item in value if isinstance(item, dict)] if isinstance(value, list) else []
