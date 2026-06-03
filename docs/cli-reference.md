# CLI Reference — MisakaNet

## `search_knowledge.py` — Core Search Tool

```bash
python3 search_knowledge.py <query> [options]
```

| Argument | Target | Description | Example |
|----------|--------|-------------|---------|
| `query` | (positional) | Search keywords | `python3 search_knowledge.py "pip install timeout"` |
| `--lessons` | Filter | Search only `lessons/` | `--lessons` |
| `--ref` | Filter | Search only `reference/` | `--ref` |
| `--top=<N>` | Pagination | Show top N results (default: 10) | `--top=3` |
| `--titles` | Display | Show titles only | `--titles` |
| `--broad` | Matching | Broader keyword matching | `--broad` |
| `--suggest` | Mode | List matching titles (≥2 chars) | `--suggest` |
| `--semantic` | Mode | Use sentence-transformers _(optional dep)_ | `--semantic` |
| `--score` | Mode | Lesson quality scoring from telemetry | `--score --top=5` |
| `--telemetry=<path>` | Scoring | Custom telemetry DB path | `--telemetry=/tmp/t.db --score` |

**Exit codes:** `0` = results found, `1` = no results or error.

## Other CLI Tools

| Command | Description |
|---------|-------------|
| `python3 scripts/new_lesson.py` | Interactive lesson generator |
| `python3 misakanet/scripts/queue_lesson.py` | Queue a lesson via CLI args |
| `python3 search_knowledge.py --score` | Telemetry-based lesson ranking |
| `python3 -m misakanet.tools.dashboard` | Launch telemetry dashboard (stdlib HTTP server) |

## Environment

| Variable | Default | Description |
|----------|---------|-------------|
| `MISAKANET_HOME` | `~/.misakanet` | Data directory (cache, telemetry DB) |
| `MISAKANET_TELEMETRY` | `$MISAKANET_HOME/langchain_telemetry.db` | Telemetry database path |

## Hub (Advanced)

| Command | Description |
|---------|-------------|
| `python3 hub/misaka_hub.py` | Start Hub orchestration server |
| `python3 -m misakanet.scripts.hub_poller` | Poll Hub for new lessons |

> Requires: `pip install -r hub/requirements.txt`
