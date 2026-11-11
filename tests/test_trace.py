"""Tests for trace.py (stdlib unittest only)."""

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import trace  # noqa: E402


def load_example(name):
    return json.loads((ROOT / "examples" / name).read_text(encoding="utf-8"))


class TestValidate(unittest.TestCase):
    def test_valid_session_passes(self):
        steps = load_example("session.json")
        self.assertEqual(trace.validate_session(steps), [])

    def test_broken_session_fails_with_right_errors(self):
        steps = load_example("broken-session.json")
        errors = trace.validate_session(steps)
        self.assertTrue(errors, "broken session should produce errors")
        joined = "\n".join(errors)
        self.assertIn("unknown action 'hover'", joined)
        self.assertIn("non-monotonic timestamp", joined)


class TestTranscript(unittest.TestCase):
    def test_transcript_contains_step_numbers_and_urls(self):
        steps = load_example("session.json")
        text = trace.transcript_text(steps)
        self.assertIn("1. [0.0s] navigate", text)
        self.assertIn("https://docs.python.org/3/library/unittest.html", text)
        self.assertIn("7. [3.5s] evaluate", text)


class TestReplay(unittest.TestCase):
    def test_replay_round_trips_step_count(self):
        steps = load_example("session.json")
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "replay.json"
            result = subprocess.run(
                [sys.executable, str(ROOT / "trace.py"), "replay",
                 str(ROOT / "examples" / "session.json"), "-o", str(out)],
                capture_output=True, text=True,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            replayed = json.loads(out.read_text(encoding="utf-8"))
        self.assertEqual(len(replayed), len(steps))
        self.assertEqual(
            [s["action"] for s in replayed], [s["action"] for s in steps]
        )


class TestCliExitCodes(unittest.TestCase):
    def test_validate_cli_exits_nonzero_on_broken_session(self):
        result = subprocess.run(
            [sys.executable, str(ROOT / "trace.py"), "validate",
             str(ROOT / "examples" / "broken-session.json")],
            capture_output=True, text=True,
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("unknown action", result.stderr)


if __name__ == "__main__":
    unittest.main()
