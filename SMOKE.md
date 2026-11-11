# SMOKE — agent-browser-trace

Run from `/home/hatch/workspace/github-factory/2026-11-10/agent-browser-trace/`
on 2026-11-10. Python 3, stdlib only, no network. All commands below were
actually run; exit codes are real.

## Commands and exit codes

| # | Command | Exit |
|---|---------|------|
| 1 | `python3 -m unittest discover -s tests -v` | 0 (5 tests, OK) |
| 2 | `python3 trace.py validate examples/session.json` | 0 (`OK: 7 step(s) valid`) |
| 3 | `python3 trace.py transcript examples/session.json --report report.md` | 0 (7-line transcript printed, `report.md` written) |
| 4 | `python3 trace.py replay examples/session.json -o replay.json` | 0 (`replay written to replay.json (7 step(s))`, replay re-read: 7 steps) |
| 5 | `python3 trace.py validate examples/broken-session.json` | 2 (expected non-zero) |

## Broken-session errors (command 5, stderr, verbatim)

```
error: step 3: non-monotonic timestamp 0.4 < previous ts 0.5
error: step 3: unknown action 'hover' (expected one of click, evaluate, navigate, screenshot, scroll, type, wait)
invalid: 2 error(s)
```

Both deliberate errors in `examples/broken-session.json` (unknown action
`hover`, non-monotonic timestamp) were caught.

## Notes

- `replay.json` and `report.md` in this directory are generated outputs
  from commands 3–4; both are listed in `.gitignore`.
- No failures. Nothing was pushed; no GitHub repo was created; no login
  was performed.
