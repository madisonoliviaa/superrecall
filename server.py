"""
SuperRecall — Semantic Search for SuperPlane Workflow Issues
REST API server backed by ChromaDB for vector search.

Run: uvicorn server:app --host 0.0.0.0 --port 8042 --reload
"""

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional, List
import chromadb
import uuid
import json
from datetime import datetime, timezone

# ── App ──────────────────────────────────────────────────────────────
app = FastAPI(
    title="SuperRecall",
    description="Semantic search for SuperPlane workflow issues. "
                "Log what went wrong, what fixed it, and search by meaning — not keywords.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── ChromaDB ─────────────────────────────────────────────────────────
chroma = chromadb.PersistentClient(path="./data/chromadb")
collection = chroma.get_or_create_collection(
    name="workflow_issues",
    metadata={"hnsw:space": "cosine"},
)


# ── Models ───────────────────────────────────────────────────────────
class WorkflowIssue(BaseModel):
    service: str = Field(..., description="Affected service (e.g. Redis, API, PostgreSQL)")
    environment: str = Field(..., description="Environment: prod | staging | dev")
    error_message: str = Field(..., description="The error message or symptom observed")
    root_cause: str = Field(..., description="What actually caused the issue")
    fix_applied: str = Field(..., description="What fixed it")
    severity: str = Field(default="P2", description="P1 (critical) | P2 (major) | P3 (minor)")
    tags: Optional[List[str]] = Field(default=[], description="Categorization tags")
    workflow_name: Optional[str] = Field(default="", description="SuperPlane canvas/workflow name")
    additional_notes: Optional[str] = Field(default="", description="Extra context")


class SearchResponse(BaseModel):
    query: str
    results: list
    count: int


# ── Helpers ──────────────────────────────────────────────────────────
def _build_document(issue: WorkflowIssue) -> str:
    """Build a rich text document for embedding."""
    parts = [
        f"Service: {issue.service}",
        f"Environment: {issue.environment}",
        f"Error: {issue.error_message}",
        f"Root Cause: {issue.root_cause}",
        f"Fix: {issue.fix_applied}",
        f"Severity: {issue.severity}",
    ]
    if issue.workflow_name:
        parts.append(f"Workflow: {issue.workflow_name}")
    if issue.tags:
        parts.append(f"Tags: {', '.join(issue.tags)}")
    if issue.additional_notes:
        parts.append(f"Notes: {issue.additional_notes}")
    return "\n".join(parts)


# ── Routes ───────────────────────────────────────────────────────────
@app.post("/api/issues", status_code=201)
async def log_issue(issue: WorkflowIssue):
    """Log a workflow issue to the semantic knowledge base."""
    issue_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()

    collection.add(
        ids=[issue_id],
        documents=[_build_document(issue)],
        metadatas=[{
            "service": issue.service,
            "environment": issue.environment,
            "error_message": issue.error_message,
            "root_cause": issue.root_cause,
            "fix_applied": issue.fix_applied,
            "severity": issue.severity,
            "workflow_name": issue.workflow_name or "",
            "tags": json.dumps(issue.tags or []),
            "additional_notes": issue.additional_notes or "",
            "timestamp": now,
        }],
    )

    return {
        "id": issue_id,
        "status": "logged",
        "timestamp": now,
        "message": f"Issue logged: {issue.service} / {issue.environment}",
    }


@app.get("/api/search")
async def search_issues(
    q: str = Query(..., description="Natural-language search query"),
    limit: int = Query(default=5, ge=1, le=20),
):
    """Semantic search across all logged workflow issues."""
    total = collection.count()
    if total == 0:
        return {"query": q, "results": [], "count": 0}

    results = collection.query(
        query_texts=[q],
        n_results=min(limit, total),
    )

    formatted = []
    for i, doc in enumerate(results["documents"][0]):
        meta = results["metadatas"][0][i] if results["metadatas"] else {}
        distance = results["distances"][0][i] if results["distances"] else None
        similarity = round(1 - distance, 4) if distance is not None else None

        formatted.append({
            "id": results["ids"][0][i],
            "similarity": similarity,
            "service": meta.get("service", ""),
            "environment": meta.get("environment", ""),
            "error_message": meta.get("error_message", ""),
            "root_cause": meta.get("root_cause", ""),
            "fix_applied": meta.get("fix_applied", ""),
            "severity": meta.get("severity", ""),
            "workflow_name": meta.get("workflow_name", ""),
            "tags": json.loads(meta.get("tags", "[]")),
            "timestamp": meta.get("timestamp", ""),
            "additional_notes": meta.get("additional_notes", ""),
        })

    return {"query": q, "results": formatted, "count": len(formatted)}


@app.get("/api/issues")
async def list_issues(limit: int = Query(default=20, ge=1, le=100)):
    """List all logged workflow issues."""
    total = collection.count()
    if total == 0:
        return {"issues": [], "count": 0}

    results = collection.get(limit=min(limit, total))

    issues = []
    for i, doc in enumerate(results["documents"]):
        meta = results["metadatas"][i] if results["metadatas"] else {}
        issues.append({
            "id": results["ids"][i],
            "service": meta.get("service", ""),
            "environment": meta.get("environment", ""),
            "error_message": meta.get("error_message", ""),
            "root_cause": meta.get("root_cause", ""),
            "fix_applied": meta.get("fix_applied", ""),
            "severity": meta.get("severity", ""),
            "timestamp": meta.get("timestamp", ""),
        })

    return {"issues": issues, "count": len(issues)}


@app.get("/api/health")
async def health():
    """Health check endpoint."""
    return {"status": "ok", "issues_count": collection.count()}


# ── Run ──────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8042)
