from __future__ import annotations

import json
import threading
from pathlib import Path
from typing import Any


class JsonStore:
    def __init__(self, path: Path) -> None:
        self._path = path
        self._path.parent.mkdir(parents=True, exist_ok=True)
        if not self._path.exists():
            self._path.write_text("{}", encoding="utf-8")
        self._lock = threading.Lock()

    def _read(self) -> dict[str, Any]:
        with self._lock:
            try:
                raw = self._path.read_text(encoding="utf-8")
                if not raw.strip():
                    return {}
                return json.loads(raw)
            except json.JSONDecodeError:  # pragma: no cover - defensive guard
                return {}

    def _write(self, data: dict[str, Any]) -> None:
        serialized = json.dumps(data, indent=2, ensure_ascii=False)
        with self._lock:
            temp_path = self._path.with_suffix(".tmp")
            temp_path.write_text(serialized, encoding="utf-8")
            temp_path.replace(self._path)
