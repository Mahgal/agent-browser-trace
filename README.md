# agent-browser-trace

Agent-browser sessions are hard to debug when a run goes wrong — this tool validates an agent-browser-style session log, prints a readable transcript, and emits a normalised replay file, so you can see exactly what the agent did, step by step.

No browser required: it only reads session JSON. Python 3.10+ standard library only, no dependencies, no network calls.

## Quick start

```bash
python trace.py validate examples/session.json
python trace.py transcript examples/session.json
python trace.py replay examples/session.json -o replay.json
```

Validate a broken log (exits non-zero and names the offending steps):

```bash
python trace.py validate examples/broken-session.json
```

## Session format

A session is a JSON list of steps. Each step has an `action`, a `ts`
(seconds since the session started, monotonic), and fields per action:

| action     | required fields      |
| ---------- | -------------------- |
| navigate   | `url` (http/https)   |
| click      | `selector`           |
| type       | `selector`, `text`   |
| scroll     | `direction` (up/down/left/right) |
| screenshot | `path`               |
| wait       | `ms` (integer >= 0)  |
| evaluate   | `expression`         |

Validation rejects unknown actions, missing required fields, malformed
URLs, bad `wait`/`scroll` values, and non-monotonic timestamps.

## Example output

Real output of `python trace.py transcript examples/session.json`:

```
1. [0.0s] navigate https://docs.python.org/3/library/unittest.html
2. [0.5s] wait 500ms
3. [1.2s] type #search -> 'mock'
4. [1.8s] click a[href='/3/library/unittest.mock.html']
5. [2.4s] scroll down
6. [3.0s] screenshot shots/unittest-docs.png
7. [3.5s] evaluate document.title
```

`transcript` and `validate` also accept `--report report.md` to write a
Markdown report alongside the console output.

## Tests

```bash
python -m unittest discover -s tests -v
```

## License

MIT — see [LICENSE](LICENSE).
