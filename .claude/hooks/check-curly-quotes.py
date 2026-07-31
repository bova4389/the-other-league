#!/usr/bin/env python3
"""PostToolUse hook: catch Unicode curly quotes in edited JS/HTML.

Why this exists
---------------
Editing tools sometimes substitute Unicode curly quotes for ASCII ones. On these
static sites that has bitten us twice:

  1. Curly SINGLE quotes where JS expects '  -> Uncaught SyntaxError, and the whole
     ES module fails to load, taking every feature with it.
  2. Curly DOUBLE quotes used as HTML attribute delimiters inside a JS string ->
     perfectly valid JavaScript, NO error anywhere, but the emitted HTML is broken.
     A browser reads id=”foo” as an unquoted value, so the real id becomes ”foo”
     and getElementById('foo') returns null. This one sat in production undetected
     until a specific tab-switch path was exercised.

Case 2 throws nothing, so a human or a test run will not notice it. Hence a hook.

Contract: reads the hook JSON on stdin, always exits 0 (advisory, never blocks a
write), and prints a JSON object only when there is something to report.
"""
import json
import re
import sys

# U+2018/19 = curly single, U+201C/1D = curly double
CURLY_SINGLE = "‘’"
CURLY_DOUBLE = "“”"
# An attribute delimiter is a curly double quote immediately after '=' -> the silent bug
ATTR_DELIM = re.compile(r"=[“”]")
# Mojibake from a UTF-8/cp1252 round-trip also contains U+201D, but always beside
# U+00E2. Those are cosmetic (they live in comments) and must not raise a false alarm.
MOJIBAKE = re.compile(r"â[“”€†]")


def _is_apostrophe(text: str, i: int) -> bool:
    """True when a curly single quote is punctuation inside text, not a code delimiter.

    Legitimate display strings contain typographic apostrophes — e.g.
    picksName: 'Mayo’s picks' — which are valid JS and must not be flagged, or the
    hook cries wolf and gets ignored. Distinguish by context:

      * U+2019 (right) preceded by a letter/digit is an apostrophe: Mayo’s, don’t,
        players’ — a real delimiter is essentially never preceded by a word char.
      * U+2018 (left) is rarely a legitimate apostrophe, so only treat it as one when
        it sits between two word characters.

    A misused pair still trips the check via its OPENING quote (preceded by '=', '(',
    ',', ':' or whitespace), so catching one of the two is enough to raise the alarm.
    """
    prev_ch = text[i - 1] if i > 0 else ""
    next_ch = text[i + 1] if i + 1 < len(text) else ""
    if text[i] == "’":
        return prev_ch.isalnum()
    return prev_ch.isalnum() and next_ch.isalnum()


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except Exception:
        return 0  # not our business if the payload is unreadable

    ti = payload.get("tool_input") or {}
    tr = payload.get("tool_response") or {}
    path = ti.get("file_path") or (tr.get("filePath") if isinstance(tr, dict) else None)
    if not path or not str(path).lower().endswith((".js", ".html", ".htm")):
        return 0

    try:
        with open(path, "r", encoding="utf-8", errors="replace") as fh:
            text = fh.read()
    except OSError:
        return 0

    # Strip mojibake runs before counting so they don't inflate the numbers.
    scrubbed = MOJIBAKE.sub("", text)

    attr_hits = [m.start() for m in ATTR_DELIM.finditer(scrubbed)]
    single_hits = [i for i, ch in enumerate(scrubbed) if ch in CURLY_SINGLE
                   and not _is_apostrophe(scrubbed, i)]

    if not attr_hits and not single_hits:
        return 0

    def line_of(idx: int) -> int:
        return scrubbed.count("\n", 0, idx) + 1

    problems = []
    if attr_hits:
        lines = sorted({line_of(i) for i in attr_hits})
        problems.append(
            f"{len(attr_hits)} curly double-quote(s) used as HTML attribute "
            f"delimiters on line(s) {lines[:12]}{'...' if len(lines) > 12 else ''} "
            f"— these produce BROKEN HTML with no JS error"
        )
    if single_hits:
        lines = sorted({line_of(i) for i in single_hits})
        problems.append(
            f"{len(single_hits)} curly single-quote(s) on line(s) "
            f"{lines[:12]}{'...' if len(lines) > 12 else ''} "
            f"— will throw SyntaxError if they are in JS code rather than text"
        )

    detail = "; ".join(problems)
    out = {
        "systemMessage": f"Curly-quote check FAILED on {path}: {detail}",
        "hookSpecificOutput": {
            "hookEventName": "PostToolUse",
            "additionalContext": (
                f"WARNING - the curly-quote hook found problems in {path}: {detail}. "
                "Replace them with ASCII quotes (\" and '), limiting the replacement to "
                "the affected lines so legitimate curly quotes in comments or display "
                "text are preserved. Then verify the repair (e.g. diff the function "
                "against a known-good sibling). Do not leave this for the user to find."
            ),
        },
    }
    print(json.dumps(out))
    return 0


if __name__ == "__main__":
    sys.exit(main())
