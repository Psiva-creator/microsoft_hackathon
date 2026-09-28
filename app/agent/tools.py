import json
from typing import Any, Callable

from app.adapters.mock import get_mock_adapters
from app.memory.retrieval import recall
from app.memory.store import get_incident, get_runbook, get_service_dependencies
from app.models import Cue

# JSON Schemas for Anthropic Tool Calling
TOOL_SCHEMAS = [
    {
        "name": "search_past_incidents",
        "description": "Searches long-term episodic memory for past incidents matching symptoms or errors.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search query or symptoms"},
                "services": {"type": "array", "items": {"type": "string"}},
                "limit": {"type": "integer", "default": 5},
            },
            "required": ["query"],
        },
    },
    {
        "name": "get_incident",
        "description": "Retrieves the full record of a specific past incident by ID.",
        "input_schema": {
            "type": "object",
            "properties": {
                "incident_id": {"type": "string", "description": "e.g. INC-0007"},
            },
            "required": ["incident_id"],
        },
    },
    {
        "name": "get_runbook",
        "description": "Fetches a procedural runbook including body instructions and success statistics.",
        "input_schema": {
            "type": "object",
            "properties": {
                "runbook_id": {"type": "string", "description": "e.g. RB-db-pool-exhaustion"},
            },
            "required": ["runbook_id"],
        },
    },
    {
        "name": "get_recent_deploys",
        "description": "Queries recent deployments for a service.",
        "input_schema": {
            "type": "object",
            "properties": {
                "service": {"type": "string"},
                "hours": {"type": "integer", "default": 6},
            },
            "required": ["service"],
        },
    },
    {
        "name": "query_logs",
        "description": "Queries redacted live or recent application logs for a service.",
        "input_schema": {
            "type": "object",
            "properties": {
                "service": {"type": "string"},
                "query": {"type": "string", "default": ""},
                "minutes": {"type": "integer", "default": 30},
                "limit": {"type": "integer", "default": 50},
            },
            "required": ["service"],
        },
    },
    {
        "name": "get_metrics",
        "description": "Queries telemetry time-series metrics for a service (returns min, max, last, trend, points).",
        "input_schema": {
            "type": "object",
            "properties": {
                "service": {"type": "string"},
                "metric": {"type": "string"},
                "minutes": {"type": "integer", "default": 60},
            },
            "required": ["service", "metric"],
        },
    },
    {
        "name": "get_service_dependencies",
        "description": "Queries the service architecture graph for upstream and downstream dependencies.",
        "input_schema": {
            "type": "object",
            "properties": {
                "service": {"type": "string"},
            },
            "required": ["service"],
        },
    },
    {
        "name": "find_code_history",
        "description": "Inspects commit log and file changes related to a path or commit hash.",
        "input_schema": {
            "type": "object",
            "properties": {
                "file_path": {"type": "string"},
                "commit_sha": {"type": "string"},
            },
        },
    },
    {
        "name": "submit_analysis",
        "description": "Submits the final structured investigation analysis, terminating the reasoning loop.",
        "input_schema": {
            "type": "object",
            "properties": {
                "summary": {"type": "string"},
                "precedent_strength": {"type": "string", "enum": ["strong", "partial", "none"]},
                "hypotheses": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "rank": {"type": "integer"},
                            "cause": {"type": "string"},
                            "confidence": {"type": "string", "enum": ["low", "medium", "high"]},
                            "evidence_for": {"type": "array", "items": {"type": "string"}},
                            "evidence_against": {"type": "array", "items": {"type": "string"}},
                            "similar_incidents": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "id": {"type": "string"},
                                        "why_similar": {"type": "string"},
                                        "differences": {"type": "string"},
                                    },
                                    "required": ["id", "why_similar", "differences"],
                                },
                            },
                            "recommended_steps": {"type": "array", "items": {"type": "string"}},
                            "runbook_id": {"type": ["string", "null"]},
                            "risk_notes": {"type": ["string", "null"]},
                        },
                        "required": ["rank", "cause", "confidence", "recommended_steps"],
                    },
                },
                "what_to_check_next": {"type": "array", "items": {"type": "string"}},
                "needs_human_decision": {"type": "array", "items": {"type": "string"}},
            },
            "required": [
                "summary",
                "precedent_strength",
                "hypotheses",
                "what_to_check_next",
                "needs_human_decision",
            ],
        },
    },
]


def create_tool_dispatcher(
    scenario_name: str | None = None,
) -> Callable[[str, dict[str, Any]], str]:
    """Creates a strictly read-only dispatcher routing tool calls to memory or mock adapters."""
    log_adapter, metrics_adapter, deploy_adapter, code_adapter = get_mock_adapters(scenario_name)

    def dispatch(tool_name: str, args: dict[str, Any]) -> str:
        if tool_name == "search_past_incidents":
            q = args.get("query", "")
            svcs = args.get("services", [])
            k = args.get("limit", 5)
            cue = Cue(text=q, services=svcs)
            res = recall(cue, top_k=k)
            out = [
                {
                    "id": i.id,
                    "title": i.title,
                    "final": i.final,
                    "flags": i.flags,
                    "summary": i.summary,
                }
                for i in res.incidents
            ]
            return json.dumps(out, indent=2)

        elif tool_name == "get_incident":
            inc_id = args.get("incident_id", "")
            rec = get_incident(inc_id)
            if not rec:
                return f"Incident {inc_id} not found."
            # Exclude large vector fields for clean LLM prompt context
            cleaned = {k: v for k, v in rec.items() if not k.startswith("emb_")}
            return json.dumps(cleaned, indent=2, default=str)

        elif tool_name == "get_runbook":
            rb_id = args.get("runbook_id", "")
            rb = get_runbook(rb_id)
            if not rb:
                return f"Runbook {rb_id} not found."
            return json.dumps(rb.model_dump(), indent=2, default=str)

        elif tool_name == "get_recent_deploys":
            svc = args.get("service", "")
            hrs = args.get("hours", 6)
            deploys = deploy_adapter.recent(svc, hours=hrs)
            return json.dumps([d.__dict__ for d in deploys], indent=2)

        elif tool_name == "query_logs":
            svc = args.get("service", "")
            q = args.get("query", "")
            mins = args.get("minutes", 30)
            limit = args.get("limit", 50)
            logs = log_adapter.query(svc, query=q, minutes=mins, limit=limit)
            return json.dumps([log_line.__dict__ for log_line in logs], indent=2)

        elif tool_name == "get_metrics":
            svc = args.get("service", "")
            m = args.get("metric", "")
            mins = args.get("minutes", 60)
            points = metrics_adapter.query(svc, metric=m, minutes=mins)
            if not points:
                return json.dumps({"points": [], "summary": "No telemetry data"})
            vals = [p.value for p in points]
            summary = {
                "min": min(vals),
                "max": max(vals),
                "last": vals[-1],
                "trend": "rising" if vals[-1] > vals[0] else "falling",
                "sample_count": len(vals),
            }
            return json.dumps(
                {"summary": summary, "samples": [p.__dict__ for p in points[:20]]}, indent=2
            )

        elif tool_name == "get_service_dependencies":
            svc = args.get("service", "")
            deps = get_service_dependencies(svc)
            return json.dumps(deps, indent=2)

        elif tool_name == "find_code_history":
            fp = args.get("file_path")
            sha = args.get("commit_sha")
            if sha:
                c = code_adapter.commit(sha)
                return json.dumps(c.__dict__ if c else {}, indent=2)
            elif fp:
                commits = code_adapter.history(fp)
                return json.dumps([c.__dict__ for c in commits], indent=2)
            return json.dumps([])

        elif tool_name == "submit_analysis":
            return "Analysis submitted."

        raise ValueError(f"Unknown read-only tool: {tool_name}")

    return dispatch
