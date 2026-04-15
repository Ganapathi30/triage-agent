import json
from pathlib import Path


def load_triage_queue(path: Path) -> list[dict]:
    if not path.exists():
        return []
    try:
        with path.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
        return data if isinstance(data, list) else []
    except json.JSONDecodeError:
        return []


def save_triage_queue(path: Path, queue: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(queue, handle, indent=2)


def append_triage_entry(path: Path, entry: dict) -> None:
    queue = load_triage_queue(path)
    queue.append(entry)
    save_triage_queue(path, queue)
