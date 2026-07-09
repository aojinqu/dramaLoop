import sys
from types import SimpleNamespace

from fastapi.testclient import TestClient
from typer.testing import CliRunner

import dramaloop.main as main_module
from dramaloop.web.app import create_app


runner = CliRunner()


def test_health_endpoint_returns_ok() -> None:
    client = TestClient(create_app())

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_web_command_starts_uvicorn_with_factory(monkeypatch) -> None:
    calls: dict[str, object] = {}

    def fake_run(app: str, **kwargs: object) -> None:
        calls["app"] = app
        calls.update(kwargs)

    monkeypatch.setitem(sys.modules, "uvicorn", SimpleNamespace(run=fake_run))

    result = runner.invoke(
        main_module.app,
        ["web", "--host", "0.0.0.0", "--port", "9000", "--reload"],
    )

    assert result.exit_code == 0
    assert calls == {
        "app": "dramaloop.web.app:create_app",
        "host": "0.0.0.0",
        "port": 9000,
        "reload": True,
        "factory": True,
    }
