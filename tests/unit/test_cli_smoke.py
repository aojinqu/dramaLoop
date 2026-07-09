from typer.testing import CliRunner

from dramaloop.main import app


runner = CliRunner()


def test_cli_help_lists_core_commands() -> None:
    result = runner.invoke(app, ["--help"])

    assert result.exit_code == 0
    assert "run" in result.stdout
    assert "inspect" in result.stdout
    assert "eval" in result.stdout
