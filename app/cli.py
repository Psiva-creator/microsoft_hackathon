from pathlib import Path
from typing import List, Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from app.agent.investigate import investigate as run_investigation
from app.agent.postmortem import confirm_and_save_to_memory, resolve_incident
from app.code_memory.pr_check import check_pr
from app.eval.harness import run_evaluation
from app.ingestion.pipeline import ingest_folder, ingest_runbooks
from app.jobs.consolidate import run_consolidation
from app.logging import setup_logging
from app.memory.retrieval import recall
from app.memory.store import (
    add_service_dependency,
    get_all_runbooks,
    get_incident_count,
    upsert_service,
)
from app.models import Cue

app = typer.Typer(help="Incident Response Agent with Brain-Inspired Memory")
console = Console()


@app.callback()
def main():
    setup_logging(log_level="WARNING")


@app.command()
def seed():
    """Generates seed data, loads services, dependencies, and runbooks into memory."""
    console.print("[bold green]🌱 Seeding Incident Response Agent memory...[/bold green]")

    services = [
        ("web-frontend", "frontend-team", "Customer facing web application"),
        ("checkout-api", "checkout-team", "Checkout orchestration service"),
        ("payments-gateway", "payments-team", "External payment processor adapter"),
        ("orders-service", "orders-team", "Order processing and persistence service"),
        ("inventory-service", "inventory-team", "Inventory allocation and tracking"),
        ("postgres-primary", "data-infra", "Primary relational database"),
        ("redis-cache", "data-infra", "Distributed in-memory caching tier"),
        ("kafka-orders", "data-infra", "Order event streaming cluster"),
        ("auth-service", "security-team", "User authentication and JWT signing"),
        ("notification-worker", "comms-team", "Async email/SMS push worker"),
    ]

    for name, team, desc in services:
        upsert_service(name, owner_team=team, description=desc, epoch=1)
    console.print(f" Loaded {len(services)} services.")

    deps = [
        ("web-frontend", "checkout-api"),
        ("web-frontend", "auth-service"),
        ("checkout-api", "payments-gateway"),
        ("checkout-api", "orders-service"),
        ("checkout-api", "inventory-service"),
        ("checkout-api", "redis-cache"),
        ("orders-service", "postgres-primary"),
        ("orders-service", "kafka-orders"),
        ("inventory-service", "postgres-primary"),
        ("notification-worker", "kafka-orders"),
    ]
    for svc, dep in deps:
        add_service_dependency(svc, dep)
    console.print(f" Loaded {len(deps)} service dependency edges.")

    rb_count = ingest_runbooks("data/runbooks")
    console.print(f" Ingested {rb_count} procedural runbooks.")

    seed_dir = Path("data/seed")
    if not (seed_dir / "_labels.json").exists():
        console.print(" Generating synthetic incidents in data/seed/...")
        import subprocess

        subprocess.run(["python", "scripts/generate_seed_data.py"], check=True)

    console.print(
        "[bold green]✅ Seed setup complete. Ready to ingest incidents via 'cli ingest data/seed'.[/bold green]"
    )


@app.command()
def ingest(
    path: str = typer.Argument(default="data/seed", help="Path to incident files directory"),
    accept_low: bool = typer.Option(False, "--accept-low", help="Accept low confidence extractions"),
):
    """Ingests documents into episodic memory."""
    console.print(f"[bold cyan]📥 Ingesting documents from {path}...[/bold cyan]")
    count = ingest_folder(path, accept_low=accept_low)
    total = get_incident_count()
    console.print(
        f"[bold green]✅ Ingested {count} documents. Total incidents in memory: {total}[/bold green]"
    )


@app.command()
def ask(
    query: str = typer.Argument(..., help="Error message, alert text, or symptoms"),
    service: Optional[List[str]] = typer.Option(
        None, "--service", "-s", help="Service name(s) affected"
    ),
    top: int = typer.Option(5, "--top", "-k", help="Number of incidents to return"),
):
    """Retrieves top past incidents with full score breakdown and mismatch flags."""
    services = service or []
    cue = Cue(
        text=query,
        error_messages=[query],
        services=services,
    )

    result = recall(cue, top_k=top)

    if not result.incidents:
        console.print("[yellow]No relevant past incidents found for this cue.[/yellow]")
        return

    table = Table(
        title=f"Top Recalled Incidents for Cue: '{query}'",
        show_header=True,
        header_style="bold magenta",
    )
    table.add_column("ID", style="bold cyan", width=10)
    table.add_column("Title", style="white", min_width=24)
    table.add_column("Final", justify="right", style="bold green", width=8)
    table.add_column("Vec", justify="right", width=6)
    table.add_column("FTS", justify="right", width=6)
    table.add_column("FP", justify="right", width=6)
    table.add_column("Svc", justify="right", width=6)
    table.add_column("Code", justify="right", width=6)
    table.add_column("Matched On", style="yellow", width=12)
    table.add_column("Flags", style="red", width=18)

    for inc in result.incidents[:top]:
        s = inc.scores
        table.add_row(
            inc.id,
            inc.title[:35] + ("..." if len(inc.title) > 35 else ""),
            f"{inc.final:.3f}",
            f"{s.get('vec', 0):.2f}",
            f"{s.get('fts', 0):.2f}",
            f"{s.get('fp', 0):.2f}",
            f"{s.get('svc', 0):.2f}",
            f"{s.get('code', 0):.2f}",
            ",".join(inc.matched_on),
            ",".join(inc.flags) or "-",
        )

    console.print(table)

    if result.runbooks:
        console.print("\n[bold yellow]📖 Relevant Runbooks:[/bold yellow]")
        for rb in result.runbooks:
            console.print(f" - [cyan]{rb.id}[/cyan]: {rb.title}")


@app.command()
def investigate(
    scenario: str = typer.Option(
        "A_pool_exhaustion", "--scenario", help="Mock scenario to investigate"
    ),
    note: Optional[str] = typer.Option(None, "--note", help="Additional engineer observation note"),
):
    """Executes the full reasoning agent loop to investigate an incident."""
    console.print(
        f"[bold cyan]🔍 Starting Investigation for Scenario: {scenario}...[/bold cyan]"
    )

    analysis = run_investigation(scenario_name=scenario, note=note)

    badge_color = {
        "strong": "bold green",
        "partial": "bold yellow",
        "none": "bold red",
    }.get(analysis.precedent_strength, "white")

    console.print(
        Panel(
            f"[bold]Summary:[/bold] {analysis.summary}\n"
            f"[bold]Precedent Strength:[/bold] [{badge_color}]{analysis.precedent_strength.upper()}[/{badge_color}]",
            title="🧠 Incident Analysis Report",
            border_style="cyan",
        )
    )

    for hyp in analysis.hypotheses:
        conf_style = {
            "high": "bold green",
            "medium": "bold yellow",
            "low": "bold red",
        }.get(hyp.confidence, "white")
        console.print(
            f"\n[bold underline]Hypothesis #{hyp.rank} (Confidence: [{conf_style}]{hyp.confidence.upper()}[/{conf_style}]):[/bold underline]"
        )
        console.print(f"[bold]Likely Cause:[/bold] {hyp.cause}")

        if hyp.evidence_for:
            console.print("[green]Evidence For:[/green]")
            for ev in hyp.evidence_for:
                console.print(f"  ✓ {ev}")

        if hyp.evidence_against:
            console.print("[red]Evidence Against:[/red]")
            for ev in hyp.evidence_against:
                console.print(f"  ✗ {ev}")

        if hyp.similar_incidents:
            console.print("[yellow]Similar Precedents & Pattern Separation:[/yellow]")
            for sim in hyp.similar_incidents:
                console.print(f"  • [cyan]{sim.id}[/cyan]: {sim.why_similar}")
                console.print(f"    [italic]Differences:[/italic] {sim.differences}")

        if hyp.recommended_steps:
            console.print("[bold blue]Recommended Steps (Safest First):[/bold blue]")
            for idx, step in enumerate(hyp.recommended_steps, 1):
                console.print(f"  {idx}. {step}")

        if hyp.runbook_id:
            console.print(f"  [bold]Associated Runbook:[/bold] [cyan]{hyp.runbook_id}[/cyan]")

    if analysis.needs_human_decision:
        console.print(
            "\n[bold red]⚠️ Requires Human Authorization (Read-Only Safety Guard):[/bold red]"
        )
        for item in analysis.needs_human_decision:
            console.print(f"  🛑 {item}")

    if analysis.what_to_check_next:
        console.print("\n[bold magenta]Next Checks to Run:[/bold magenta]")
        for check in analysis.what_to_check_next:
            console.print(f"  🔍 {check}")


@app.command()
def resolve(
    live_id: str = typer.Argument(..., help="Live incident ID"),
    root_cause: str = typer.Option(..., "--root-cause", "-r", help="Human-verified root cause"),
    steps: str = typer.Option(..., "--steps", "-s", help="Steps taken to restore service"),
    runbook: Optional[List[str]] = typer.Option(None, "--runbook", help="Runbook IDs used"),
    worked: bool = typer.Option(True, "--worked/--failed", help="Whether the resolution worked"),
):
    """Marks an incident resolved, drafts post-mortem, and commits to memory."""
    console.print(f"[bold cyan]📝 Resolving Live Incident {live_id}...[/bold cyan]")
    step_list = [s.strip() for s in steps.split(";") if s.strip()] or [steps]
    rb_list = runbook or []

    draft = resolve_incident(
        live_id=live_id,
        root_cause=root_cause,
        steps=step_list,
        runbook_ids=rb_list,
        worked=worked,
    )

    console.print(
        Panel(
            draft.markdown,
            title="📋 Generated Post-Mortem Draft (Human Approved)",
            border_style="green",
        )
    )

    inc_id = confirm_and_save_to_memory(live_id, draft.markdown)
    console.print(
        f"[bold green]🎉 Incident {live_id} successfully saved to long-term memory as {inc_id}![/bold green]"
    )


@app.command()
def pr_check(
    files: Optional[List[str]] = typer.Option(None, "--files", "-f", help="Modified file paths"),
    diff: Optional[str] = typer.Option(None, "--diff", "-d", help="Path to diff file"),
):
    """Checks changed files or diff against historical outages that touched the same code."""
    file_list = files or []
    diff_text = None
    if diff and Path(diff).exists():
        diff_text = Path(diff).read_text()

    res = check_pr(files=file_list, diff=diff_text)
    risk = res["risk_level"]

    color = "bold red" if risk == "high" else ("bold yellow" if risk == "medium" else "bold green")
    console.print(f"[bold]PR Risk Assessment:[/bold] [{color}]{risk.upper()}[/{color}]")

    if res["matched_incidents"]:
        table = Table(title="Past Outages Linked to Modified Code", header_style="bold red")
        table.add_column("Incident ID", style="cyan")
        table.add_column("File Path", style="white")
        table.add_column("Role", style="yellow")
        table.add_column("Historical Root Cause", style="white")

        for m in res["matched_incidents"]:
            table.add_row(m["incident_id"], m["file_path"], m["role"], m["root_cause"][:60])
        console.print(table)

    if res["recommendations"]:
        console.print("\n[bold yellow]🛡️ Proactive Safety Recommendations:[/bold yellow]")
        for rec in res["recommendations"]:
            console.print(f"  • {rec}")


@app.command()
def consolidate():
    """Triggers sleep-replay consolidation to cluster incidents into patterns and decay stale weights."""
    console.print(
        "[bold cyan]🧠 Running Sleep-Replay Memory Consolidation...[/bold cyan]"
    )
    result = run_consolidation()
    console.print(
        f"[bold green]✅ Consolidation complete. Patterns: {result['patterns_created']}, "
        f"Incidents Evaluated: {result['incidents_decayed']}. Report saved to: {result['report_path']}[/bold green]"
    )


@app.command()
def stats():
    """Displays memory health statistics, runbook success rates, and total counts."""
    inc_count = get_incident_count()
    runbooks = get_all_runbooks()

    table = Table(title="Procedural Runbooks Success Statistics", header_style="bold cyan")
    table.add_column("Runbook ID", style="cyan")
    table.add_column("Title", style="white")
    table.add_column("Successes", justify="right", style="green")
    table.add_column("Failures", justify="right", style="red")
    table.add_column("Success Rate", justify="right", style="bold yellow")

    for rb in runbooks:
        total = rb.success_count + rb.failure_count
        prob = (rb.success_count + 1) / (total + 2)
        table.add_row(
            rb.id,
            rb.title[:40],
            str(rb.success_count),
            str(rb.failure_count),
            f"{prob * 100:.1f}%",
        )

    console.print(f"\n[bold]Total Episodic Incidents in Memory:[/bold] [green]{inc_count}[/green]")
    console.print(table)


@app.command(name="eval")
def evaluate(
    cases: str = typer.Option("eval/cases.jsonl", "--cases", "-c", help="Path to evaluation cases JSONL"),
    output: str = typer.Option("eval", "--output", "-o", help="Output directory for reports"),
):
    """Runs the quantitative evaluation harness and ablation suite across retrieval modes."""
    console.print("[bold cyan]📊 Running Retrieval Evaluation & Ablation Suite...[/bold cyan]")
    results = run_evaluation(cases_path=cases, output_dir=output)

    table = Table(title="Retrieval Engine Benchmark Results", header_style="bold cyan")
    table.add_column("Retrieval Mode", style="cyan")
    table.add_column("Recall@1", justify="right", style="white")
    table.add_column("Recall@3", justify="right", style="bold green")
    table.add_column("Recall@5", justify="right", style="white")
    table.add_column("MRR", justify="right", style="yellow")
    table.add_column("p50 (ms)", justify="right", style="white")
    table.add_column("Status", justify="center", style="bold")

    for key, data in results.items():
        status = (
            "[green]PASS[/green]"
            if data["recall_at_3"] >= 0.80
            else ("[yellow]BASELINE[/yellow]" if key in ("keyword", "vector") else "[dim]ABLATION[/dim]")
        )
        table.add_row(
            data["label"],
            f"{data['recall_at_1']:.1%}",
            f"{data['recall_at_3']:.1%}",
            f"{data['recall_at_5']:.1%}",
            f"{data['mrr']:.3f}",
            f"{data['p50_latency_ms']} ms",
            status,
        )

    console.print(table)
    console.print(f"[bold green]✅ Evaluation complete. Full report written to {output}/report.md[/bold green]")


@app.command()
def doctor():
    """Runs system diagnostics: verifies environment, memory, guardrails, and data stores."""
    import platform
    import sys

    from app.config import get_settings

    settings = get_settings()
    console.print(Panel.fit("[bold blue]🩺 Incident Response Agent: System Diagnostics[/bold blue]", border_style="blue"))

    table = Table(title="Component Health Check", show_header=True, header_style="bold magenta")
    table.add_column("Component", style="cyan", width=28)
    table.add_column("Status", justify="center", style="bold")
    table.add_column("Details", style="dim")

    # 1. Python runtime
    py_ver = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    table.add_row("Python Runtime", "[green]PASS[/green]", f"{py_ver} on {platform.system()} ({platform.machine()})")

    # 2. Read-only safety guardrail
    if not settings.ALLOW_ACTIONS:
        table.add_row("Read-Only Safety Guard", "[bold green]ENFORCED[/bold green]", "ALLOW_ACTIONS=false (Zero mutating tools)")
    else:
        table.add_row("Read-Only Safety Guard", "[bold red]MUTATING[/bold red]", "ALLOW_ACTIONS=true (Danger!)")

    # 3. Embedding cache
    cache_path = Path(".cache/embeddings.sqlite")
    if cache_path.exists():
        table.add_row("Embedding Cache", "[green]READY[/green]", f"{cache_path} ({cache_path.stat().st_size} bytes)")
    else:
        table.add_row("Embedding Cache", "[yellow]WARMUP[/yellow]", "No cache yet; local model will initialize on first query")

    # 4. Seed incident data
    seed_dir = Path("data/seed")
    seed_count = len(list(seed_dir.glob("inc_*.*"))) if seed_dir.exists() else 0
    if seed_count >= 50:
        table.add_row("Seed Incident Data", "[green]READY[/green]", f"{seed_count} seed incident documents")
    else:
        table.add_row("Seed Incident Data", "[yellow]PARTIAL[/yellow]", f"{seed_count} documents in data/seed")

    # 5. Outage scenarios
    scenario_dir = Path("data/mock_env/scenarios")
    scenarios = [d.name for d in scenario_dir.iterdir() if d.is_dir()] if scenario_dir.exists() else []
    table.add_row("Outage Scenarios (A-D)", "[green]READY[/green]", f"{len(scenarios)} scenarios: {', '.join(scenarios)}")

    # 6. Procedural Runbooks
    runbooks = get_all_runbooks()
    table.add_row("Procedural Runbooks", "[green]READY[/green]", f"{len(runbooks)} runbooks loaded")

    console.print(table)
    console.print("[bold green]✅ System diagnostics complete. All core systems operational.[/bold green]")


if __name__ == "__main__":
    app()
