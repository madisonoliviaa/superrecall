"""
SuperRecall — MCP Server
Exposes semantic workflow search as MCP tools for AI agents (Claude, Cursor, etc.)

Run: python mcp_server.py
Or configure in your MCP client's settings.
"""

from mcp.server.fastmcp import FastMCP
import chromadb
import json
import uuid
from datetime import datetime, timezone

# ── MCP Server ───────────────────────────────────────────────────────
mcp = FastMCP(
    "SuperRecall",
    description="Semantic search for SuperPlane workflow issues. "
                "Search past incidents by meaning, log new fixes, and build team knowledge.",
)

# ── ChromaDB (same data directory as the REST API) ───────────────────
chroma = chromadb.PersistentClient(path="./data/chromadb")
collection = chroma.get_or_create_collection(
    name="workflow_issues",
    metadata={"hnsw:space": "cosine"},
)


# ── Tools ────────────────────────────────────────────────────────────
@mcp.tool()
def search_workflow_issues(query: str, limit: int = 5) -> str:
    """
    Semantic search across all logged workflow issues.
    Ask natural questions like:
    - "Redis connection problems on staging"
    - "deploy keeps failing after merge"
    - "database timeout during migration"
    Returns the most similar past issues with their fixes.
    """
    total = collection.count()
    if total == 0:
        return json.dumps({"message": "No issues logged yet.", "results": []})

    results = collection.query(
        query_texts=[query],
        n_results=min(limit, total),
    )

    formatted = []
    for i, doc in enumerate(results["documents"][0]):
        meta = results["metadatas"][0][i] if results["metadatas"] else {}
        distance = results["distances"][0][i] if results["distances"] else None
        similarity = round(1 - distance, 4) if distance is not None else None

        formatted.append({
            "similarity": similarity,
            "service": meta.get("service", ""),
            "environment": meta.get("environment", ""),
            "error_message": meta.get("error_message", ""),
            "root_cause": meta.get("root_cause", ""),
            "fix_applied": meta.get("fix_applied", ""),
            "severity": meta.get("severity", ""),
            "timestamp": meta.get("timestamp", ""),
        })

    return json.dumps({"query": query, "results": formatted, "count": len(formatted)}, indent=2)


@mcp.tool()
def log_workflow_issue(
    service: str,
    environment: str,
    error_message: str,
    root_cause: str,
    fix_applied: str,
    severity: str = "P2",
    tags: str = "",
    workflow_name: str = "",
    notes: str = "",
) -> str:
    """
    Log a new workflow issue to the knowledge base.
    Provide structured details so the team can find this later via semantic search.

    Args:
        service: Affected service (e.g. "Redis", "API", "PostgreSQL", "GitHub Actions")
        environment: Environment where it happened (prod, staging, dev)
        error_message: The error or symptom observed
        root_cause: What actually caused the issue
        fix_applied: What you did to fix it
        severity: P1 (critical), P2 (major), P3 (minor)
        tags: Comma-separated tags (e.g. "redis,config,timeout")
        workflow_name: SuperPlane canvas/workflow name if applicable
        notes: Any extra context
    """
    issue_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    tag_list = [t.strip() for t in tags.split(",") if t.strip()] if tags else []

    document = "\n".join([
        f"Service: {service}",
        f"Environment: {environment}",
        f"Error: {error_message}",
        f"Root Cause: {root_cause}",
        f"Fix: {fix_applied}",
        f"Severity: {severity}",
        f"Workflow: {workflow_name}" if workflow_name else "",
        f"Tags: {', '.join(tag_list)}" if tag_list else "",
        f"Notes: {notes}" if notes else "",
    ])

    collection.add(
        ids=[issue_id],
        documents=[document.strip()],
        metadatas=[{
            "service": service,
            "environment": environment,
            "error_message": error_message,
            "root_cause": root_cause,
            "fix_applied": fix_applied,
            "severity": severity,
            "workflow_name": workflow_name,
            "tags": json.dumps(tag_list),
            "additional_notes": notes,
            "timestamp": now,
        }],
    )

    return json.dumps({
        "status": "logged",
        "id": issue_id,
        "message": f"Issue logged: {service} / {environment} — searchable immediately.",
    })


@mcp.tool()
def find_similar_failures(error_message: str, limit: int = 3) -> str:
    """
    Given a current error message, find the most similar past failures and their fixes.
    Use this when actively troubleshooting — paste the error and get back what worked before.
    """
    total = collection.count()
    if total == 0:
        return json.dumps({"message": "No past issues to compare against.", "results": []})

    results = collection.query(
        query_texts=[error_message],
        n_results=min(limit, total),
    )

    formatted = []
    for i, doc in enumerate(results["documents"][0]):
        meta = results["metadatas"][0][i] if results["metadatas"] else {}
        distance = results["distances"][0][i] if results["distances"] else None
        similarity = round(1 - distance, 4) if distance is not None else None

        formatted.append({
            "similarity": similarity,
            "error_message": meta.get("error_message", ""),
            "root_cause": meta.get("root_cause", ""),
            "fix_applied": meta.get("fix_applied", ""),
            "service": meta.get("service", ""),
            "environment": meta.get("environment", ""),
        })

    return json.dumps({
        "current_error": error_message,
        "similar_past_issues": formatted,
        "count": len(formatted),
    }, indent=2)


@mcp.tool()
def list_recent_issues(limit: int = 10) -> str:
    """List the most recently logged workflow issues."""
    total = collection.count()
    if total == 0:
        return json.dumps({"message": "No issues logged yet.", "issues": []})

    results = collection.get(limit=min(limit, total))

    issues = []
    for i, doc in enumerate(results["documents"]):
        meta = results["metadatas"][i] if results["metadatas"] else {}
        issues.append({
            "service": meta.get("service", ""),
            "environment": meta.get("environment", ""),
            "error_message": meta.get("error_message", ""),
            "fix_applied": meta.get("fix_applied", ""),
            "severity": meta.get("severity", ""),
            "timestamp": meta.get("timestamp", ""),
        })

    return json.dumps({"issues": issues, "count": len(issues)}, indent=2)


# ── Run ──────────────────────────────────────────────────────────────
if __name__ == "__main__":
    mcp.run()
