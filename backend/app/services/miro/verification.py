"""Read-back comparison for the exact subset of Miro fields managed by this app."""

from decimal import Decimal, InvalidOperation
from html.parser import HTMLParser
import re
from typing import Any


class PlainText(HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts: list[str] = []

    def handle_data(self, data: str) -> None:
        self.parts.append(data)

    def handle_starttag(self, tag: str, attrs) -> None:
        if tag in ["br", "p", "div", "li"]:
            self.parts.append(" ")

    def handle_endtag(self, tag: str) -> None:
        if tag in ["p", "div", "li"]:
            self.parts.append(" ")


def text_content(value: str) -> str:
    parser = PlainText()
    parser.feed(value)
    return " ".join("".join(parser.parts).split())


def payload_mismatches(expected: dict, actual: dict, prefix: str = "") -> list[str]:
    mismatches = []
    numeric = {"x", "y", "width", "height", "fontSize"}
    for key, want in expected.items():
        field = f"{prefix}.{key}" if prefix else key
        if key not in actual:
            mismatches.append(field)
            continue
        got = actual[key]
        if isinstance(want, dict):
            mismatches.extend(payload_mismatches(want, got, field) if isinstance(got, dict) else [field])
        elif key == "content" and isinstance(want, str) and isinstance(got, str):
            if text_content(want) != text_content(got):
                mismatches.append(field)
        elif key in numeric:
            try:
                if abs(Decimal(str(want)) - Decimal(str(got))) > Decimal("0.01"):
                    mismatches.append(field)
            except InvalidOperation:
                mismatches.append(field)
        elif got != want:
            mismatches.append(field)
    return mismatches


def unrelated_snapshot(items: list[dict], managed_ids: set[str]) -> dict[str, Any]:
    fields = {
        "type",
        "data",
        "style",
        "position",
        "geometry",
        "parent",
        "startItem",
        "endItem",
        "shape",
        "captions",
    }
    return {
        str(item["id"]): {k: v for k, v in item.items() if k in fields}
        for item in items
        if str(item["id"]) not in managed_ids
    }


def board_id_from_url(value: str) -> str:
    from urllib.parse import urlparse, unquote

    if value.startswith("https://"):
        parsed = urlparse(value)
        if parsed.hostname not in ["miro.com", "www.miro.com"]:
            raise ValueError("Expected a Miro board URL")
        match = re.fullmatch(r"/app/board/([^/]+)/?", parsed.path)
        if not match:
            raise ValueError("Expected /app/board/<id>/")
        value = unquote(match.group(1))
    if not re.fullmatch(r"[A-Za-z0-9_=:-]{1,100}", value):
        raise ValueError("Invalid Miro board ID")
    return value
