"""Provider-independent publication with durable item mappings and write journal."""

import html
import re
import time
from typing import Protocol, Any
from urllib.parse import quote
import httpx
from app.core.utils import digest, uid
from app.persistence.store import Store
from app.services.miro.scene import BoardScene, PublicationOperation
from app.services.miro.verification import payload_mismatches


class MiroError(Exception):
    def __init__(self, message: str, ambiguous: bool = False):
        super().__init__(message)
        self.ambiguous = ambiguous


class MiroAdapter(Protocol):
    mode: str

    def create_board(self, name: str) -> dict: ...
    def get_board(self, board_id: str) -> dict: ...
    def create_items(self, board_id: str, items: list[dict]) -> list[dict]: ...
    def update_item(self, board_id: str, item_id: str, item: dict) -> dict: ...
    def list_managed_items(self, board_id: str) -> list[dict]: ...
    def reconcile_publication(self, board_id: str, scene: BoardScene) -> dict: ...


def path_id(value: str) -> str:
    if not re.fullmatch(r"[A-Za-z0-9_=:-]{1,100}", value):
        raise MiroError("Invalid remote identifier")
    return quote(value, safe="")


def scene_payloads(scene: BoardScene) -> list[dict]:
    result = []
    for section in scene.sections:
        result.append(
            {
                "key": f"frame-{section.key}",
                "type": "frame",
                "data": {"title": section.title, "type": "freeform"},
                "position": {
                    "x": section.x + section.width / 2,
                    "y": section.y + section.height / 2,
                    "origin": "center",
                },
                "geometry": {"width": section.width, "height": section.height},
            }
        )
        for item in section.items:
            content = html.escape(item.content).replace("\n", "<br>")
            if item.evidence_reference_ids:
                content += "<br>Sources: " + html.escape(", ".join(item.evidence_reference_ids))
            payload: dict[str, Any] = {
                "key": item.key,
                "type": item.kind,
                "data": {"content": content},
                "position": {"x": item.x + item.width / 2, "y": item.y + item.height / 2, "origin": "center"},
                "geometry": {"width": item.width},
            }
            if item.kind == "shape":
                payload["data"]["shape"] = "rectangle"
                payload["geometry"]["height"] = item.height
                payload["style"] = {"fillColor": item.style.fill, "fontSize": "14", "textAlign": "left"}
            elif item.kind == "sticky_note":
                payload["data"]["shape"] = "square"
                payload["style"] = {"fillColor": "light_yellow"}
            result.append(payload)
    for connector in scene.connectors:
        result.append(
            {
                "key": connector.key,
                "type": "connector",
                "start_key": connector.start_key,
                "end_key": connector.end_key,
            }
        )
    return result


class Reconciler:
    mode: str
    store: Store

    def get_board(self, board_id: str) -> dict:
        raise NotImplementedError

    def create_items(self, board_id: str, items: list[dict]) -> list[dict]:
        raise NotImplementedError

    def update_item(self, board_id: str, item_id: str, item: dict) -> dict:
        raise NotImplementedError

    def list_managed_items(self, board_id: str) -> list[dict]:
        return [m for m in self.store.all("mapping") if m["board_id"] == board_id and m["mode"] == self.mode]

    def reconcile_publication(self, board_id: str, scene: BoardScene) -> dict:
        path_id(board_id)
        self.get_board(board_id)
        existing = {m["key"]: m for m in self.list_managed_items(board_id)}
        result: dict[str, Any] = {
            "created": 0,
            "updated": 0,
            "unchanged": 0,
            "retained_stale": 0,
            "mode": self.mode,
        }
        payloads = scene_payloads(scene)
        for raw in payloads:
            key = raw["key"]
            mapping_id = f"{self.mode}:{board_id}:{key}"
            payload: dict[str, Any] = {k: v for k, v in raw.items() if k != "key"}
            if payload["type"] == "connector":
                if raw["start_key"] not in existing or raw["end_key"] not in existing:
                    raise MiroError("Connector endpoints unavailable")
                payload = {
                    "type": "connector",
                    "startItem": {"id": existing[raw["start_key"]]["remote_id"]},
                    "endItem": {"id": existing[raw["end_key"]]["remote_id"]},
                    "shape": "elbowed",
                }
            checksum = digest(payload)
            previous = existing.get(key)
            if previous and previous["payload_hash"] == checksum:
                result["unchanged"] += 1
                continue
            pending = [
                op
                for op in self.store.all("operation")
                if op["board_id"] == f"{self.mode}:{board_id}"
                and op["item_key"] == key
                and op["status"] in ["STARTED", "AMBIGUOUS"]
            ]
            if pending:
                raise MiroError(
                    "Ambiguous prior write requires manual mapping reconciliation", ambiguous=True
                )
            op = PublicationOperation(
                id=uid("OP"),
                board_id=f"{self.mode}:{board_id}",
                item_key=key,
                operation="update" if previous else "create",
                payload_hash=checksum,
                status="STARTED",
            )
            self.store.put("operation", op.id, op)
            try:
                remote = (
                    self.update_item(board_id, previous["remote_id"], payload)
                    if previous
                    else self.create_items(board_id, [payload])[0]
                )
                remote_id = str(remote["id"])
                mapping = {
                    "id": mapping_id,
                    "board_id": board_id,
                    "mode": self.mode,
                    "key": key,
                    "remote_id": remote_id,
                    "payload_hash": checksum,
                    "type": payload["type"],
                }
                self.store.put("mapping", mapping_id, mapping)
                existing[key] = mapping
                op.status = "SUCCEEDED"
                op.remote_id = remote_id
                result["updated" if previous else "created"] += 1
            except (MiroError, KeyError, IndexError, TypeError) as exc:
                ambiguous = not isinstance(exc, MiroError) or exc.ambiguous
                op.status = "AMBIGUOUS" if ambiguous else "FAILED"
                self.store.put("operation", op.id, op)
                raise MiroError(
                    "Publication incomplete; inspect operation journal before retrying", ambiguous
                ) from None
            self.store.put("operation", op.id, op)
        result["retained_stale"] = len(set(existing) - {p["key"] for p in payloads})
        return result


class MockMiroAdapter(Reconciler):
    mode = "mock"

    def __init__(self, store: Store, fail_after: int | None = None):
        self.store = store
        self.fail_after = fail_after
        self.calls = 0

    def create_board(self, name: str) -> dict:
        board = {"id": f"mock-{digest(name)[:12]}", "name": name, "mode": "mock"}
        self.store.put("mock_board", board["id"], board)
        return board

    def get_board(self, board_id: str) -> dict:
        return self.store.get("mock_board", board_id)

    def create_items(self, board_id: str, items: list[dict]) -> list[dict]:
        self.get_board(board_id)
        if len(items) > 20:
            raise MiroError("Maximum 20 items per batch")
        results = []
        for item in items:
            if item["type"] not in ["frame", "shape", "text", "sticky_note", "connector"]:
                raise MiroError("Unsupported item type")
            if self.fail_after is not None and self.calls >= self.fail_after:
                raise MiroError("Simulated partial failure")
            self.calls += 1
            remote = {**item, "id": uid("MOCK"), "board_id": board_id}
            self.store.put("mock_item", remote["id"], remote)
            results.append(remote)
        return results

    def update_item(self, board_id: str, item_id: str, item: dict) -> dict:
        old = self.store.get("mock_item", item_id)
        if old["board_id"] != board_id:
            raise MiroError("Board mismatch")
        updated = {**old, **item}
        self.store.put("mock_item", item_id, updated)
        return updated


class RestMiroAdapter(Reconciler):
    mode = "live"
    routes = {
        "frame": "frames",
        "shape": "shapes",
        "text": "texts",
        "sticky_note": "sticky_notes",
        "connector": "connectors",
    }

    def __init__(self, store: Store, token: str, enabled: bool = False, client: httpx.Client | None = None):
        if not enabled or not token:
            raise MiroError("Live Miro is disabled or OAuth token unavailable")
        self.store = store
        self.client = client or httpx.Client(base_url="https://api.miro.com/v2", timeout=10, trust_env=False)
        self._token = token

    def request(self, method: str, route: str, payload=None, params: dict | None = None) -> dict:
        for attempt in range(3):
            try:
                response = self.client.request(
                    method,
                    route,
                    json=payload,
                    params=params,
                    headers={"Authorization": f"Bearer {self._token}"},
                    timeout=10,
                )
            except httpx.HTTPError:
                self.store.audit("miro", "request_transport_failure", route, "provider", method=method)
                if method == "POST":
                    raise MiroError("Ambiguous create; no automatic replay", True) from None
                if attempt == 2:
                    raise MiroError("Miro transport unavailable") from None
                time.sleep(0.2 * (attempt + 1))
                continue
            self.store.audit(
                "miro", "request_status", route, "provider", method=method, status=response.status_code
            )
            if response.status_code == 429:
                if attempt == 2:
                    raise MiroError("Miro rate limit retry budget exhausted")
                try:
                    delay = float(response.headers.get("Retry-After", "1"))
                except ValueError:
                    delay = 1
                if delay > 2:
                    raise MiroError("Miro rate limit requires later retry")
                time.sleep(max(0, delay))
                continue
            if response.status_code >= 500:
                if method == "POST":
                    raise MiroError("Ambiguous create response; no automatic replay", True)
                if attempt < 2:
                    time.sleep(0.2 * (attempt + 1))
                    continue
            if response.is_error:
                raise MiroError(f"Miro request rejected ({response.status_code})")
            try:
                body = response.json()
                if not isinstance(body, dict):
                    raise ValueError("Expected a response object")
                return body
            except ValueError:
                raise MiroError("Malformed Miro response", method == "POST") from None
        raise MiroError("Miro request unavailable")

    def create_board(self, name: str) -> dict:
        return self.request(
            "POST",
            "/boards",
            {"name": name[:60], "description": "Synthetic manufacturing review; no launch authorisation"},
        )

    def get_board(self, board_id: str) -> dict:
        return self.request("GET", f"/boards/{path_id(board_id)}")

    def create_items(self, board_id: str, items: list[dict]) -> list[dict]:
        if len(items) > 20:
            raise MiroError("Maximum 20 items per call")
        # Individual creates preserve exact per-item write journals and avoid relying
        # on bulk response ordering. Frames/connectors have separate schemas.
        result = []
        for item in items:
            route = self.routes.get(item["type"])
            if route is None:
                raise MiroError("Unsupported item type")
            result.append(
                self.request(
                    "POST",
                    f"/boards/{path_id(board_id)}/{route}",
                    {k: v for k, v in item.items() if k != "type"},
                )
            )
        return result

    def update_item(self, board_id: str, item_id: str, item: dict) -> dict:
        route = self.routes.get(item["type"])
        if route is None:
            raise MiroError("Unsupported item type")
        return self.request(
            "PATCH",
            f"/boards/{path_id(board_id)}/{route}/{path_id(item_id)}",
            {k: v for k, v in item.items() if k != "type"},
        )

    def get_item(self, board_id: str, item_id: str, item_type: str) -> dict:
        route = self.routes.get(item_type)
        if route is None:
            raise MiroError("Unsupported item type")
        result = self.request("GET", f"/boards/{path_id(board_id)}/{route}/{path_id(item_id)}")
        if str(result.get("id", "")) != item_id:
            raise MiroError("Miro read-back returned an unexpected item ID")
        return result

    def list_board_items(self, board_id: str, max_pages: int = 100) -> list[dict]:
        if not 1 <= max_pages <= 100:
            raise MiroError("Invalid pagination budget")
        combined: dict[str, dict] = {}
        for resource in ["items", "connectors"]:
            cursor = None
            seen: set[str] = set()
            for _ in range(max_pages):
                params = {"limit": 50}
                if cursor is not None:
                    params["cursor"] = cursor
                body = self.request("GET", f"/boards/{path_id(board_id)}/{resource}", params=params)
                items = body.get("data")
                if not isinstance(items, list) or any(
                    not isinstance(i, dict) or not i.get("id") for i in items
                ):
                    raise MiroError("Malformed Miro page")
                for item in items:
                    combined[str(item["id"])] = item
                cursor = body.get("cursor")
                if not cursor:
                    break
                if not isinstance(cursor, str) or cursor in seen:
                    raise MiroError("Invalid Miro pagination cursor")
                seen.add(cursor)
            else:
                raise MiroError("Miro pagination budget exhausted; validation incomplete")
        return list(combined.values())

    def verify_managed_items(self, board_id: str, scene: BoardScene) -> dict:
        mappings = {m["key"]: m for m in self.list_managed_items(board_id)}
        checked = 0
        for raw in scene_payloads(scene):
            mapping = mappings.get(raw["key"])
            if mapping is None:
                raise MiroError("Managed mapping is missing; verification incomplete")
            expected = {k: v for k, v in raw.items() if k != "key"}
            if raw["type"] == "connector":
                expected = {
                    "type": "connector",
                    "startItem": {"id": mappings[raw["start_key"]]["remote_id"]},
                    "endItem": {"id": mappings[raw["end_key"]]["remote_id"]},
                    "shape": "elbowed",
                }
            actual = self.get_item(board_id, mapping["remote_id"], mapping["type"])
            differences = payload_mismatches(expected, actual)
            if differences:
                # Safe field paths only: never echo remote content or provider errors.
                self.store.audit("miro", "readback_mismatch", mapping["key"], "provider", fields=differences)
                raise MiroError("Remote managed content differs from the approved scene")
            checked += 1
        return {"verified_items": checked, "readback": "matched_approved_scene"}
