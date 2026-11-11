import json
import sqlite3
from pathlib import Path
from threading import RLock
from typing import Any
from app.core.utils import uid
from app.domain.models import AuditEvent


class Store:
    def __init__(self, path: str):
        if path != ":memory:":
            Path(path).parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(path, check_same_thread=False)
        self.db.execute("PRAGMA journal_mode=WAL")
        self.db.execute(
            "CREATE TABLE IF NOT EXISTS records (kind TEXT, id TEXT, body TEXT, PRIMARY KEY(kind,id))"
        )
        self.db.commit()
        self.lock = RLock()

    def put(self, kind: str, key: str, value: Any) -> Any:
        body = value.model_dump(mode="json") if hasattr(value, "model_dump") else value
        with self.lock, self.db:
            self.db.execute(
                "INSERT INTO records VALUES(?,?,?) ON CONFLICT(kind,id) DO UPDATE SET body=excluded.body",
                (kind, key, json.dumps(body)),
            )
        return value

    def get(self, kind: str, key: str) -> dict:
        with self.lock:
            row = self.db.execute("SELECT body FROM records WHERE kind=? AND id=?", (kind, key)).fetchone()
        if row is None:
            raise KeyError(f"{kind} {key} not found")
        return json.loads(row[0])

    def all(self, kind: str) -> list[dict]:
        with self.lock:
            return [
                json.loads(r[0])
                for r in self.db.execute("SELECT body FROM records WHERE kind=? ORDER BY id", (kind,))
            ]

    def audit(self, actor: str, event: str, entity: str, correlation: str, **details: Any) -> None:
        a = AuditEvent(
            id=uid("AUD"),
            actor=actor,
            event=event,
            entity_id=entity,
            correlation_id=correlation,
            details=details,
        )
        self.put("audit", a.id, a)

    def claim_publication(self, publication: dict) -> bool:
        with self.lock, self.db:
            active = self.db.execute(
                "SELECT id FROM records WHERE kind='publication' AND json_extract(body,'$.status')='PUBLISHING'"
            ).fetchone()
            if active:
                return False
            self.db.execute(
                "INSERT INTO records VALUES(?,?,?)",
                ("publication", publication["id"], json.dumps(publication)),
            )
        return True
