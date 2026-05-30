# SuperRecall

> **Semantic search for SuperPlane workflow issues.**
> Your team's collective ops memory — log what went wrong, what fixed it, and search by *meaning*, not keywords.

[![Launch in SuperPlane](https://img.shields.io/badge/Launch%20in-SuperPlane-blue?style=for-the-badge)](https://app.superplane.com/import?repo=https://github.com/YOUR_USERNAME/superrecall)

---

## The Problem

Your ops team has **collective amnesia**. Every workflow issue gets solved from scratch because nobody remembers that the same thing happened 3 months ago. The fix is buried in a Slack thread nobody can find.

Google and GitHub search use **keyword matching** — search for "database won't connect" and you'll never find the issue titled "Redis pool exhausted." And neither knows YOUR infrastructure, YOUR configs, or YOUR team's specific fixes.

## The Solution

SuperRecall captures every workflow issue and fix, embeds them in a **vector database**, and provides **semantic search** — matching by meaning, not keywords.

- **Auto-captures** workflow failures from SuperPlane canvases
- **Engineers log fixes** with structured fields (service, error, root cause, fix)
- **Semantic search** finds similar past issues even with different wording
- **MCP server** lets AI agents (Claude, Cursor) search your team's knowledge
- **Slack notifications** surface past fixes when new issues match

### How It Works

```
Workflow fails → SuperRecall searches for similar past issues
  → Found match? → Posts the past fix to Slack: "This looks like the
    Redis issue from March 12. Last time, the fix was..."
  → No match? → Alerts team. Once fixed, engineer logs it.
    Next time, it's found instantly.
```

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│  SuperPlane Canvas                                      │
│  ┌──────────┐   ┌────────────┐   ┌──────────────────┐  │
│  │ Trigger   │──▶│ Search API │──▶│ Notify (Slack)   │  │
│  │ (failure) │   │ (similar?) │   │ + Save to Memory │  │
│  └──────────┘   └────────────┘   └──────────────────┘  │
└────────────────────────┬────────────────────────────────┘
                         │ HTTP
                         ▼
┌─────────────────────────────────────────────────────────┐
│  SuperRecall API Server (FastAPI)                       │
│  POST /api/issues    — log a new issue                  │
│  GET  /api/search    — semantic search                  │
│  GET  /api/issues    — list all issues                  │
│  GET  /api/health    — health check                     │
└────────────────────────┬────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────┐
│  ChromaDB (Vector Database)                             │
│  Embeds issues as vectors, matches by cosine similarity │
└─────────────────────────────────────────────────────────┘
                         ▲
                         │
┌─────────────────────────────────────────────────────────┐
│  MCP Server                                             │
│  Tools: search_workflow_issues, log_workflow_issue,     │
│         find_similar_failures, list_recent_issues       │
│  Connect from Claude Code, Cursor, or any MCP client    │
└─────────────────────────────────────────────────────────┘
```

## Quick Start

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Start the API server

```bash
python server.py
# Runs on http://localhost:8042
```

### 3. Seed with example data (optional)

```bash
python seed_data.py
```

### 4. Try semantic search

```bash
# Search by meaning — not keywords
curl "http://localhost:8042/api/search?q=database+connection+keeps+dropping"

# Log a new issue
curl -X POST http://localhost:8042/api/issues \
  -H "Content-Type: application/json" \
  -d '{
    "service": "Redis",
    "environment": "prod",
    "error_message": "Connection refused on port 6379",
    "root_cause": "Redis server OOM killed",
    "fix_applied": "Increased memory limit and added eviction policy",
    "severity": "P1"
  }'
```

### 5. Import the SuperPlane canvas

```bash
superplane canvases create --file canvas.yaml
```

### 6. Connect the MCP server (for AI agents)

Add to your Claude Code or Cursor MCP config:

```json
{
  "mcpServers": {
    "superrecall": {
      "command": "python",
      "args": ["path/to/superrecall/mcp_server.py"]
    }
  }
}
```

## Canvas Flows

| Flow | Trigger | What it does |
|---|---|---|
| **Auto-capture** | Workflow failure event | Searches for similar past issues → notifies Slack → saves to memory |
| **Manual log** | Engineer logs a fix | POSTs to API → confirms in Slack → searchable immediately |
| **Search** | Query from console | Semantic search → posts results to Slack |

## Tech Stack

| Component | Technology |
|---|---|
| Vector database | [ChromaDB](https://www.trychroma.com/) (open source) |
| REST API | [FastAPI](https://fastapi.tiangolo.com/) |
| MCP server | [MCP Python SDK](https://github.com/modelcontextprotocol/python-sdk) |
| Orchestration | [SuperPlane](https://superplane.com) |
| Notifications | Slack integration |

## Why Not Just Google It?

| | Google / GitHub | SuperRecall |
|---|---|---|
| **Search** | Keyword matching | Semantic (meaning-based) |
| **Context** | Generic answers | YOUR infra, YOUR configs, YOUR fixes |
| **Populated by** | Someone has to write it up | Auto-captures + manual logging |
| **Action** | Shows a page to read | AI agent reads it AND applies the fix |
| **Scope** | Per-repo / public internet | Cross-project team knowledge |

## Team

Built at SuperPlane Hackathon SFO — May 2026.

## License

MIT
