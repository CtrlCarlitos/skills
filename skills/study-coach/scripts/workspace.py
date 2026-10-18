from pathlib import Path


def resolve_workspace(path):
    path = Path(path)
    (path / "children").mkdir(parents=True, exist_ok=True)
    (path / "sources" / "mineducyt").mkdir(parents=True, exist_ok=True)
    (path / "sources" / "santillana").mkdir(parents=True, exist_ok=True)
    (path / "assets").mkdir(parents=True, exist_ok=True)
    return path


def child_dir(workspace, child_id):
    result = workspace / "children" / child_id
    (result / "subjects").mkdir(parents=True, exist_ok=True)
    return result
