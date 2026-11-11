#!/usr/bin/env python3
"""agent-browser-trace: validate, transcribe and replay agent-browser-style session logs.

A session is a JSON list of steps. Each step is an object with:

    {"action": "navigate", "ts": 0.0, "url": "https://example.com"}

``ts`` is seconds since the session started and must be monotonic
(non-decreasing). Supported actions and their required fields:

    navigate    url         (well-formed http(s) URL)
    click       selector
    type        selector, text
    scroll      direction   (up | down | left | right)
    screenshot  path
    wait        ms          (integer >= 0)
    evaluate    expression

This tool only reads session logs. It does not drive a browser and has no
network or third-party dependencies -- Python 3.10+ standard library only.

Usage:
    python trace.py validate session.json [--report report.md]
    python trace.py transcript session.json [--report report.md]
    python trace.py replay session.json -o replay.json
"""

import argparse
import json
import sys
from pathlib import Path
from urllib.parse import urlparse

ACTIONS = {"navigate", "click", "type", "scroll", "screenshot", "wait", "evaluate"}

REQUIRED_FIELDS = {
    "navigate": ["url"],
    "click": ["selector"],
    "type": ["selector", "text"],
    "scroll": ["direction"],
    "screenshot": ["path"],
    "wait": ["ms"],
    "evaluate": ["expression"],
}

SCROLL_DIRECTIONS = {"up", "down", "left", "right"}


def load_session(path):
    """Load a session file. Returns (steps, error); error is None on success."""
    try:
        text = Path(path).read_text(encoding="utf-8")
    except OSError as exc:
        return None, f"cannot read {path}: {exc}"
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        return None, f"{path}: invalid JSON: {exc}"
    if not isinstance(data, list):
        return None, f"{path}: session must be a JSON list of steps, got {type(data).__name__}"
    return data, None


def _is_valid_url(value):
    if not isinstance(value, str):
        return False
    parsed = urlparse(value)
    return parsed.scheme in ("http", "https") and bool(parsed.netloc)


def validate_session(steps):
    """Validate a list of steps. Returns a list of error strings (empty = valid)."""
    errors = []
    prev_ts = None
    for index, step in enumerate(steps, start=1):
        label = f"step {index}"
        if not isinstance(step, dict):
            errors.append(f"{label}: step must be an object, got {type(step).__name__}")
            continue
        action = step.get("action")
        ts = step.get("ts")
        if ts is None:
            errors.append(f"{label}: missing required field 'ts'")
        elif isinstance(ts, bool) or not isinstance(ts, (int, float)):
            errors.append(f"{label}: 'ts' must be a number, got {ts!r}")
        elif prev_ts is not None and ts < prev_ts:
            errors.append(
                f"{label}: non-monotonic timestamp {ts} < previous ts {prev_ts}"
            )
        else:
            prev_ts = ts
        if action is None:
            errors.append(f"{label}: missing required field 'action'")
            continue
        if action not in ACTIONS:
            errors.append(
                f"{label}: unknown action {action!r} "
                f"(expected one of {', '.join(sorted(ACTIONS))})"
            )
            continue
        for field in REQUIRED_FIELDS[action]:
            if field not in step:
                errors.append(f"{label}: action {action!r} missing required field {field!r}")
        if action == "navigate" and "url" in step and not _is_valid_url(step["url"]):
            errors.append(f"{label}: invalid URL {step['url']!r}")
        if action == "scroll" and "direction" in step and step["direction"] not in SCROLL_DIRECTIONS:
            errors.append(
                f"{label}: invalid scroll direction {step['direction']!r} "
                f"(expected one of {', '.join(sorted(SCROLL_DIRECTIONS))})"
            )
        if action == "wait" and "ms" in step:
            ms = step["ms"]
            if isinstance(ms, bool) or not isinstance(ms, int) or ms < 0:
                errors.append(f"{label}: 'ms' must be a non-negative integer, got {ms!r}")
    return errors


def _step_detail(step):
    action = step["action"]
    if action == "navigate":
        return step.get("url", "")
    if action == "click":
        return step.get("selector", "")
    if action == "type":
        return f"{step.get('selector', '')} -> {step.get('text', '')!r}"
    if action == "scroll":
        return step.get("direction", "")
    if action == "screenshot":
        return step.get("path", "")
    if action == "wait":
        return f"{step.get('ms', '')}ms"
    if action == "evaluate":
        return step.get("expression", "")
    return ""


def format_step(index, step):
    ts = step.get("ts", "?")
    return f"{index}. [{ts}s] {step['action']} {_step_detail(step)}".rstrip()


def transcript_text(steps):
    return "\n".join(format_step(i, step) for i, step in enumerate(steps, start=1))


def markdown_report(steps, source):
    lines = [
        "# Session report",
        "",
        f"Source: `{source}`",
        "",
        f"Steps: {len(steps)}",
        "",
        "## Transcript",
        "",
        "```",
        transcript_text(steps),
        "```",
        "",
    ]
    return "\n".join(lines)


def normalise_step(step):
    """Return a step with keys in a stable order (action, ts, then the rest)."""
    ordered = {}
    for key in ("action", "ts"):
        if key in step:
            ordered[key] = step[key]
    for key in sorted(step):
        if key not in ordered:
            ordered[key] = step[key]
    return ordered


def _load_or_exit(path):
    steps, error = load_session(path)
    if error is not None:
        print(f"error: {error}", file=sys.stderr)
        return None
    return steps


def _fail_validation(errors):
    for error in errors:
        print(f"error: {error}", file=sys.stderr)
    print(f"invalid: {len(errors)} error(s)", file=sys.stderr)
    return 2


def cmd_validate(args):
    steps = _load_or_exit(args.session)
    if steps is None:
        return 2
    errors = validate_session(steps)
    if errors:
        return _fail_validation(errors)
    print(f"OK: {len(steps)} step(s) valid")
    if args.report:
        Path(args.report).write_text(
            markdown_report(steps, args.session), encoding="utf-8"
        )
        print(f"report written to {args.report}")
    return 0


def cmd_transcript(args):
    steps = _load_or_exit(args.session)
    if steps is None:
        return 2
    errors = validate_session(steps)
    if errors:
        return _fail_validation(errors)
    print(transcript_text(steps))
    if args.report:
        Path(args.report).write_text(
            markdown_report(steps, args.session), encoding="utf-8"
        )
        print(f"report written to {args.report}", file=sys.stderr)
    return 0


def cmd_replay(args):
    steps = _load_or_exit(args.session)
    if steps is None:
        return 2
    errors = validate_session(steps)
    if errors:
        return _fail_validation(errors)
    replay = [normalise_step(step) for step in steps]
    text = json.dumps(replay, indent=2) + "\n"
    if args.output:
        Path(args.output).write_text(text, encoding="utf-8")
        print(f"replay written to {args.output} ({len(replay)} step(s))")
    else:
        print(text, end="")
    return 0


def build_parser():
    parser = argparse.ArgumentParser(
        prog="trace.py",
        description="Validate, transcribe and replay agent-browser-style session logs.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_validate = sub.add_parser("validate", help="validate a session JSON file")
    p_validate.add_argument("session", help="path to session JSON file")
    p_validate.add_argument("--report", help="also write a Markdown report to this path")
    p_validate.set_defaults(func=cmd_validate)

    p_transcript = sub.add_parser("transcript", help="print a human-readable transcript")
    p_transcript.add_argument("session", help="path to session JSON file")
    p_transcript.add_argument("--report", help="also write a Markdown report to this path")
    p_transcript.set_defaults(func=cmd_transcript)

    p_replay = sub.add_parser("replay", help="emit a normalised replay JSON file")
    p_replay.add_argument("session", help="path to session JSON file")
    p_replay.add_argument("-o", "--output", help="output replay JSON file (default: stdout)")
    p_replay.set_defaults(func=cmd_replay)

    return parser


def main(argv=None):
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
