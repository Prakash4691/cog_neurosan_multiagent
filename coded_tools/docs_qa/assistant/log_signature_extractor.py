import logging
import re
from typing import Any

from neuro_san.interfaces.coded_tool import CodedTool

MAX_FRAMES = 3
MAX_MESSAGE_CHARS = 300

# Before npm 10 every line starts "npm ERR!", from npm 10 "npm error".
NPM_LINE = re.compile(r"^npm (?:ERR!|error\b) ?(?P<text>.*)$")
NPM_FOUND = re.compile(r"\bFound: (?P<library>(?:@[\w.-]+/)?[\w.-]+)@(?P<version>\d[\w.+-]*)")

# MSBuild and tsc: "Program.cs(12,17): error CS0246: ..." and "src/App.tsx:5:10 - error TS2305: ...". MSBuild ends
# the line with the project in brackets, which is not part of the message.
COMPILER_ERROR = re.compile(
    r"^(?P<location>\S+?(?:\(\d+,\d+\)|:\d+:\d+))(?::| -) error (?P<code>[A-Z]+\d+): (?P<message>.+?)(?: \[[^\]]+\])?$"
)
COMPILER_LIBRARIES = {"CS": ".NET", "TS": "TypeScript"}
TARGET_FRAMEWORK = re.compile(r"TargetFramework=(?P<version>net[\w.]+)")

GO_PANIC = re.compile(r"^(?P<type>panic|fatal error): (?P<message>.+)$")
GO_SIGNAL = re.compile(r"\[signal (?P<code>SIG\w+)")
GO_VERSION = re.compile(r"\bgo(?P<version>1\.\d+(?:\.\d+)?)\b")
# "panic" is both the runtime's panic() frame and the repeated panic line of a recovered panic.
GO_INTERNAL_FRAMES = ("runtime.", "panic", "created by ")

# .NET, Java and Node.js: "Type: message", where .NET may add a "(0x80131904)" HResult and Node.js an
# "[ERR_X]" code. The prefixes mark an unhandled .NET exception, an inner .NET exception (Dataverse writes
# "----> InnerException :") and a Java cause.
EXCEPTION_LINE = re.compile(
    r"^\s*(?:Unhandled exception\.\s+|Exception in thread \"[^\"]*\"\s+|Caused by:\s+"
    r"|-{3,4}>\s+(?:InnerException\s*:\s*)?)?"
    r"(?P<type>(?:[A-Za-z_$][\w$]*\.)*(?:[A-Za-z_$][\w$]*)?(?:Exception|Error))"
    r"(?: [\[(](?P<code>0x[0-9A-Fa-f]+|[A-Z][A-Z_]+)[\])])?"
    r"(?::\s*(?P<message>.*))?$"
)
FRAME = re.compile(r"^\s*at\s+(?P<frame>\S.*)$")
# Runtime plumbing that says nothing about the error: async state machines, reflection, Node.js internals.
INTERNAL_FRAME_MARKERS = (
    "System.Runtime.CompilerServices.",
    "System.Runtime.ExceptionServices.",
    "System.Threading.Tasks.",
    "jdk.internal.",
    "sun.reflect.",
    "java.lang.reflect.",
    "node:internal/",
)
NODE_CODE = re.compile(r"^\s*code: '(?P<code>[A-Z][A-Z_]+)'", re.MULTILINE)

# A JSON error response, such as the Dataverse Web API's, puts the exception chain in one "message" string: each
# inner exception follows a "--->" in the middle of the line, and the stack trace's newlines are escaped. Only an
# escape before an "at" frame counts, so a Windows path such as C:\app\node_modules stays whole.
MID_LINE_INNER_EXCEPTION = re.compile(r"(?<=\S)[ \t]+(?=-{3,4}>[ \t])")
ESCAPED_FRAME_BREAK = re.compile(r"\\r?\\n(?=\s+at\s)")
JSON_CODE = re.compile(r'"code"\s*:\s*"(?P<code>[^"]+)"')
NODE_MODULE = re.compile(r"node_modules/(?P<library>(?:@[\w.-]+/)?[\w.-]+)/")
NODE_VERSION = re.compile(r"^Node\.js v(?P<version>\d+(?:\.\d+)*)", re.MULTILINE)

# A library named together with its version: a Java jar, a .NET assembly, a Go module path, an npm package.
VERSIONED_PACKAGES = (
    re.compile(r"(?P<library>[A-Za-z][\w.-]*?)-(?P<version>\d+(?:\.\d+)+[\w.-]*?)\.jar"),
    re.compile(r"'(?P<library>[\w.]+), Version=(?P<version>\d+(?:\.\d+)+)"),
    re.compile(r"pkg/mod/(?P<library>[^@\s]+)@(?P<version>v\d[\w.+-]*)"),
    re.compile(r"(?<![\w/.@-])(?P<library>(?:@[\w.-]+/)?[\w.-]+)@(?P<version>\d+\.\d+\.\d+[\w.+-]*)"),
)

ERROR_WORD = re.compile(r"error|exception|fail|fatal", re.IGNORECASE)


class LogSignatureExtractor(CodedTool):
    """Turns an Error Log into an Error Signature: error type or code, message, library and version, and the top
    relevant frames.

    It does no redaction. The Coordinator's middleware has already redacted the log before any LLM saw it, and the
    regexes stay there (ADR 0002).
    """

    async def async_invoke(self, args: dict[str, Any], sly_data: dict[str, Any]) -> dict[str, Any] | str:
        error_log: str = args.get("error_log") or ""
        if not error_log.strip():
            return "Error: error_log is empty. Pass the Error Log from the user's message."

        signature = extract_error_signature(error_log)
        logging.info("Error Signature: %s %s", signature["error_type"], signature["error_code"])
        return signature


def extract_error_signature(error_log: str) -> dict[str, Any]:
    error_log = ESCAPED_FRAME_BREAK.sub("\n", MID_LINE_INNER_EXCEPTION.sub("\n", error_log))
    lines = error_log.splitlines()
    # Exceptions come before npm errors: when `npm start` runs a Node.js app that throws, npm's own lines only name
    # the user's project, and the Node.js error is the one to look up.
    return (
        _compiler_signature(lines)
        or _go_panic_signature(error_log, lines)
        or _exception_signature(error_log, lines)
        or _npm_signature(error_log, lines)
        or _fallback_signature(lines)
    )


def _signature(
    *,
    error_type: str | None = None,
    error_code: str | None = None,
    message: str,
    library: str | None = None,
    version: str | None = None,
    frames: list[str] | None = None,
) -> dict[str, Any]:
    if len(message) > MAX_MESSAGE_CHARS:
        message = message[: MAX_MESSAGE_CHARS - 3] + "..."
    return {
        "error_type": error_type,
        "error_code": error_code,
        "message": message,
        "library": library,
        "version": version,
        "frames": frames or [],
    }


def _group(pattern: re.Pattern[str], text: str, group: str) -> str | None:
    match = pattern.search(text)
    return match[group] if match else None


def _compiler_signature(lines: list[str]) -> dict[str, Any] | None:
    for line in lines:
        match = COMPILER_ERROR.match(line.strip())
        if not match:
            continue
        code = match["code"]
        return _signature(
            error_code=code,
            message=match["message"],
            library=COMPILER_LIBRARIES.get(code.rstrip("0123456789")),
            version=_group(TARGET_FRAMEWORK, line, "version"),
            frames=[match["location"]],
        )
    return None


def _go_panic_signature(error_log: str, lines: list[str]) -> dict[str, Any] | None:
    panic = next((match for line in lines if (match := GO_PANIC.match(line))), None)
    if not panic:
        return None

    frames = _go_frames(lines)
    package = _find_versioned_package("\n".join(frames)) or _find_versioned_package(error_log)
    if package:
        library, version = package["library"], package["version"]
    else:
        library, version = "Go", _group(GO_VERSION, error_log, "version")
    return _signature(
        error_type=panic["type"],
        error_code=_group(GO_SIGNAL, error_log, "code"),
        message=panic["message"],
        library=library,
        version=version,
        frames=frames,
    )


def _go_frames(lines: list[str]) -> list[str]:
    """A Go frame is a function line followed by a tab-indented file:line line."""
    frames = []
    for function_line, location_line in zip(lines, lines[1:]):
        if not function_line or function_line[0].isspace() or not location_line.startswith("\t"):
            continue
        if function_line.startswith(GO_INTERNAL_FRAMES):
            continue
        frames.append(f"{function_line.strip()} {location_line.strip()}")
        if len(frames) == MAX_FRAMES:
            break
    return frames


def _exception_signature(error_log: str, lines: list[str]) -> dict[str, Any] | None:
    # The last exception line is the most specific one: the innermost .NET exception or the root Java cause.
    last_exception = None
    for index, line in enumerate(lines):
        match = EXCEPTION_LINE.match(line)
        # A bare "Error" or "TypeError" with no message is ordinary text, not an exception line.
        if match and ("." in match["type"] or match["message"] is not None):
            last_exception = index, match
    if not last_exception:
        return None

    index, exception = last_exception
    frames = _exception_frames(lines[index + 1 :])
    library, version = _exception_library(exception["type"], lines[index], frames, error_log)
    return _signature(
        error_type=exception["type"],
        error_code=exception["code"] or _group(NODE_CODE, error_log, "code") or _group(JSON_CODE, error_log, "code"),
        message=exception["message"] or "",
        library=library,
        version=version,
        frames=frames,
    )


def _exception_frames(lines: list[str]) -> list[str]:
    frames = []
    for line in lines:
        match = FRAME.match(line)
        if not match or any(marker in line for marker in INTERNAL_FRAME_MARKERS):
            continue
        # Node.js prints " {" after the last frame when the error has extra properties such as `code`.
        frames.append(match["frame"].removesuffix(" {").strip())
        if len(frames) == MAX_FRAMES:
            break
    return frames


def _exception_library(
    error_type: str, exception_line: str, frames: list[str], error_log: str
) -> tuple[str | None, str | None]:
    # Only the exception and its frames name the library. The rest of the log may name the user's own project,
    # as npm does around a Node.js error.
    evidence = "\n".join([exception_line, *frames])
    package = _find_versioned_package(evidence)
    if package:
        return package["library"], package["version"]
    node_module = _group(NODE_MODULE, evidence, "library")
    if node_module:
        return node_module, None
    node_version = _group(NODE_VERSION, error_log, "version")
    if node_version:
        return "Node.js", node_version
    if "." in error_type:
        return error_type.rsplit(".", 1)[0], None
    return None, None


def _npm_signature(error_log: str, lines: list[str]) -> dict[str, Any] | None:
    texts = [match["text"].strip() for line in lines if (match := NPM_LINE.match(line.strip()))]
    if not texts:
        return None

    code = None
    message = ""
    for text in texts:
        if text.startswith("code ") and code is None:
            code = text.removeprefix("code ").strip()
        elif text and not text.startswith("errno "):
            message = text
            break

    # "Found:" names the installed package in a dependency conflict. Without it, "While resolving:" would win,
    # and that is the user's own project.
    package = NPM_FOUND.search(error_log) or _find_versioned_package(error_log)
    if package:
        library, version = package["library"], package["version"]
    else:
        library, version = "npm", None
    return _signature(error_code=code, message=message, library=library, version=version)


def _find_versioned_package(text: str) -> re.Match[str] | None:
    for pattern in VERSIONED_PACKAGES:
        match = pattern.search(text)
        if match:
            return match
    return None


def _fallback_signature(lines: list[str]) -> dict[str, Any]:
    text_lines = [line.strip() for line in lines if line.strip()]
    message = next((line for line in text_lines if ERROR_WORD.search(line)), text_lines[0])
    return _signature(message=message)
