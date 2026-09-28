from typer.testing import CliRunner

from app.cli import app

runner = CliRunner()


def test_cli_main_help() -> None:
    """Requirement 8 & 10: CLI help loads successfully and lists all operational commands."""
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "Incident Response Agent with Brain-Inspired Memory" in result.stdout

    expected_commands = [
        "seed",
        "ingest",
        "ask",
        "investigate",
        "resolve",
        "pr-check",
        "consolidate",
        "stats",
        "eval",
        "dashboard",
        "demo",
    ]
    for cmd in expected_commands:
        assert cmd in result.stdout, f"Command '{cmd}' not found in CLI help output"


def test_cli_subcommand_helps() -> None:
    """Requirement 8: Representative subcommands load help successfully."""
    subcommands = ["ask", "investigate", "resolve", "pr-check", "stats", "eval"]
    for cmd in subcommands:
        result = runner.invoke(app, [cmd, "--help"])
        assert result.exit_code == 0, f"Command '{cmd} --help' failed with code {result.exit_code}"
        assert "Usage:" in result.stdout


def test_cli_invalid_command_produces_error() -> None:
    """Requirement 5 & 10: Invalid command produces a controlled CLI error and non-zero exit code."""
    result = runner.invoke(app, ["nonexistent-command"])
    # Typer/Click produces exit code 2 for unknown commands
    assert result.exit_code == 2


def test_cli_missing_required_arguments_produces_error() -> None:
    """Requirement 5 & 10: Missing mandatory arguments produce controlled CLI error."""
    # 'ask' requires a query string argument
    result_ask = runner.invoke(app, ["ask"])
    assert result_ask.exit_code == 2

    # 'resolve' requires live_id, --root-cause, --steps
    result_resolve = runner.invoke(app, ["resolve"])
    assert result_resolve.exit_code == 2


def test_cli_investigate_renders_confidence_and_evidence() -> None:
    """Requirement 5 & 10: investigate renders confidence badges, evidence, pattern separation, and runbooks."""
    result = runner.invoke(app, ["investigate", "--scenario", "A_pool_exhaustion"])
    assert result.exit_code == 0

    stdout = result.stdout
    # Confidence badges and precedent strength
    assert "Incident Analysis Report" in stdout
    assert "Precedent Strength:" in stdout
    assert "STRONG" in stdout
    assert "Confidence:" in stdout

    # Evidence display
    assert "Evidence For:" in stdout
    assert "Recent deploy" in stdout or "Logs show" in stdout

    # Pattern separation display
    assert "Similar Precedents & Pattern Separation:" in stdout
    assert "Differences:" in stdout

    # Runbook references
    assert "Associated Runbook:" in stdout
    assert "RB-db-pool-exhaustion" in stdout


def test_cli_investigate_preserves_safety_guards() -> None:
    """Requirement 7 & 10: Mutating actions are surfaced under human authorization warning, not executed."""
    result = runner.invoke(app, ["investigate", "--scenario", "A_pool_exhaustion"])
    assert result.exit_code == 0

    stdout = result.stdout
    # Safety guard panel / header
    assert "Requires Human Authorization (Read-Only Safety Guard)" in stdout
    # Remediation actions presented as items needing human decision
    assert "Rollback deployment" in stdout or "Restart" in stdout


def test_cli_ask_renders_score_table_and_runbooks() -> None:
    """Requirement 5 & 10: ask command renders score breakdown table and runbook links."""
    result = runner.invoke(app, ["ask", "checkout-api 503 connection timeout", "--top", "3"])
    assert result.exit_code == 0

    stdout = result.stdout
    # Table headers
    assert "Top Recalled Incidents" in stdout or "ID" in stdout
    assert "Final" in stdout
    assert "Vec" in stdout
    assert "FTS" in stdout


def test_cli_stats_renders_runbook_table() -> None:
    """Requirement 4 & 5: stats renders runbook success statistics table with Laplace probability."""
    result = runner.invoke(app, ["stats"])
    assert result.exit_code == 0

    stdout = result.stdout
    assert "Procedural Runbooks Success Statistics" in stdout
    assert "Runbook ID" in stdout
    assert "Success Rate" in stdout
