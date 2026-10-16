# 10: Error Signature from a JSON error response (Dataverse Web API)

Spec: `docs/spec/docs_qa.md` (Error logs and secret redaction).

**What to build:** `log_signature_extractor` returns a useful Error Signature when the user pastes a JSON error
response whose `message` holds the exception chain and an escaped stack trace, as the Dataverse Web API returns.

**Blocked by:** None (can start immediately)

**Status:** completed (2026-10-16)

**Found in:** manual testing in the nsflow UI, 2026-10-16 (13:14). The pasted log is saved at
`.scratch/docs_qa/dataverse_0x80048d19_log.txt`. It starts:

```text
"code": "0x80048d19",
"message": "Error identified in Payload provided by the user for Entity :'', ... ----> InnerException : Microsoft.OData.ODataException: Cannot convert the literal 'ead' to the expected type 'Edm.Int32'. ---> System.FormatException: Input string was not in a correct format.\r\n   at System.Number.StringToNumber(...)\r\n   at System.Number.ParseInt32(...)\r\n ...
```

**What happened:**

- The tool returned `error_type`, `error_code`, `library` and `version` as `null` and `frames` as `[]`. Only
  `message` was set (the fallback: the first line with an error word).
- Reproduced without the LLM by calling `extract_error_signature` on the saved log. Turning the `\r\n` escapes into
  real newlines does not help.
- Why:
  - `EXCEPTION_LINE` is anchored at the start of a line. Here every exception (`----> InnerException :
    Microsoft.OData.ODataException: ...`, `---> System.FormatException: ...`) is in the middle of the `message`
    line.
  - The frames are separated by literal `\r\n` escapes inside one JSON string, so `FRAME` never sees a line that
    starts with `at`.
  - The HResult is in a `"code": "0x80048d19"` field, which no pattern reads.
- Routing still worked (the Question went to MicrosoftLearnSpecialist), but the Specialists got no signature to
  search with.

**Acceptance criteria:**

- [x] A unit test in `tests/unit/test_log_signature_extractor.py` with this log (no secrets in it) expects:
  - `error_code` `0x80048d19`;
  - `error_type` the innermost exception, `System.FormatException`, per the existing "last exception line" rule,
    with its message;
  - the top non-internal frames from the escaped stack trace;
  - `library` as the existing rules give it.
  
  If the innermost exception is the wrong choice for this shape (the ODataException carries the useful message),
  record the decision in Notes.
- [x] The tool reads JSON-escaped newlines (`\r\n`, `\n`) inside a pasted error as line breaks, and finds an
      exception that follows a `--->` or `---->` marker in the middle of a line.
- [x] All existing extractor tests still pass. The tool stays deterministic and does no redaction (ADR 0002).

**Notes:**

- `extract_error_signature` now first:
  - puts a mid-line `--->` or `---->` marker on its own line;
  - turns an escaped `\r\n` or `\n` into a newline, but only before an indented `at ` frame, so Windows paths
    such as `C:\app\node_modules` are not split.
- `EXCEPTION_LINE` accepts `---->` and an optional `InnerException :` after the arrow.
- `error_code` falls back to a JSON `"code": "..."` field after the exception's own code and the Node.js code.
- New test `test_json_error_response_with_escaped_stack_trace_reports_the_innermost_exception_and_the_code`.
  Result for the manual-test log: `System.FormatException`, `0x80048d19`, "Input string was not in a correct
  format.", library `System`, top 3 `System.Number`/`System.String` frames.
- Kept the existing "innermost exception" rule. The ODataException message ("Cannot convert the literal 'ead' to
  the expected type 'Edm.Int32'") is more specific for this log, but changing the rule would change every .NET
  case. The `0x80048d19` code is still in the signature for the Specialist to search by.
- Unit tests passed (110, 2026-10-16).
- Live check, 2026-10-16 14:07 (nsflow UI, same log): the tool returned the signature above, and the Coordinator
  sent MicrosoftLearnSpecialist "What does error code 0x80048d19 mean and how do I fix it?" plus the signature.
  The Specialist's searches found the Dataverse Web API client-errors page, but it then timed out at 90 s while
  writing the Evidence Pack, so the user got the Microsoft Learn unavailable reply. That timeout is not this
  ticket's problem (see 09's Follow-up).
