from typer.testing import CliRunner

from app.cli import app

runner = CliRunner()


def test_cli_doctor_command():
    result = runner.invoke(app, ["doctor"])
    assert result.exit_code == 0
    assert "System Diagnostics" in result.stdout
    assert "Python Runtime" in result.stdout
    assert "Read-Only Safety Guard" in result.stdout
    assert "ENFORCED" in result.stdout
