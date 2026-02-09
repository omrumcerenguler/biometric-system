from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional


@dataclass(frozen=True)
class AuditEvent:
    event_type: str
    user_id: str
    accepted: bool
    threshold: float
    face_score: float
    voice_score: float
    fused_score: float
    reason: str
    created_at_utc: str


class AuditLogger:
    """
    Minimal, production-friendly audit logger.
    Writes JSONL (one JSON per line) for easy parsing.
    """

    def __init__(self, log_path: str = "audit.log.jsonl") -> None:
        self._path = Path(log_path)

    def log_authentication(self, event: AuditEvent) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        with self._path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(asdict(event), ensure_ascii=False) + "\n")

    @staticmethod
    def now_utc_iso() -> str:
        return datetime.now(timezone.utc).isoformat()
