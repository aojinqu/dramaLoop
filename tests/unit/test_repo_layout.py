from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


REQUIRED_PATHS = [
    "project/spec/product.md",
    "project/spec/architecture.md",
    "project/spec/evaluation.md",
    "project/spec/conventions.md",
    "project/tasks/2026-07-08-mvp-bootstrap/task.md",
    "project/tasks/2026-07-08-mvp-bootstrap/implementation-notes.md",
    "project/tasks/2026-07-08-mvp-bootstrap/status.md",
    "project/workspace/decisions.md",
    "project/workspace/learnings.md",
    "project/workspace/backlog.md",
]


def test_project_operating_layer_files_exist() -> None:
    missing = [relative_path for relative_path in REQUIRED_PATHS if not (ROOT / relative_path).exists()]

    assert missing == []
