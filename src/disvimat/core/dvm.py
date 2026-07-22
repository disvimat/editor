"""The native document format ``.dvm`` (DisViMat document).

Unlike the XHTML export, which is a presentation format, ``.dvm`` stores
the document tree exactly, so saving and reopening round-trips without
loss. It is JSON — inspectable and diff-friendly — with a version, the
language and profile it was written for, and the lines of the document.

Each node is serialised by kind::

    {"char": "1"}
    {"sign": "plus"}
    {"structure": "fraction", "slots": [[...], [...]]}

A line is a list of nodes; a document is a list of lines.
"""

import json
from dataclasses import dataclass

from disvimat.core.document import Character, Line, Node, Sign, Structure

#: File format marker and version, stored in every ``.dvm``.
FORMAT = "disvimat-document"
VERSION = 1


class DvmError(ValueError):
    """A ``.dvm`` document is malformed or of an unsupported version."""


@dataclass(frozen=True)
class DvmDocument:
    """A parsed ``.dvm``: the lines plus the metadata it was saved with."""

    lines: list[Line]
    language: str
    profile: str | None


def _node_to_json(node: Node) -> dict[str, object]:
    match node:
        case Character(text=text):
            return {"char": text}
        case Sign(element_id=element_id):
            return {"sign": element_id}
        case Structure(element_id=element_id, slots=slots):
            return {
                "structure": element_id,
                "slots": [[_node_to_json(n) for n in slot] for slot in slots],
            }


def _node_from_json(data: dict[str, object]) -> Node:
    if "char" in data:
        return Character(str(data["char"]))
    if "sign" in data:
        return Sign(str(data["sign"]))
    if "structure" in data:
        raw_slots = data.get("slots", [])
        if not isinstance(raw_slots, list):
            raise DvmError("structure slots must be a list")
        slots = [[_node_from_json(n) for n in slot] for slot in raw_slots]
        return Structure(str(data["structure"]), slots)
    raise DvmError(f"unknown node: {data!r}")


def to_dvm(lines: list[Line], *, language: str, profile: str | None = None) -> str:
    """Serialise the document lines and metadata to a ``.dvm`` string."""
    payload = {
        "format": FORMAT,
        "version": VERSION,
        "language": language,
        "profile": profile,
        "lines": [[_node_to_json(node) for node in line] for line in lines],
    }
    return json.dumps(payload, ensure_ascii=False, indent=2)


def from_dvm(text: str) -> DvmDocument:
    """Parse a ``.dvm`` string, raising :class:`DvmError` on bad input."""
    try:
        payload = json.loads(text)
    except json.JSONDecodeError as error:
        raise DvmError(f"not valid JSON: {error}") from error
    if not isinstance(payload, dict) or payload.get("format") != FORMAT:
        raise DvmError("not a DISVIMAT document")
    if payload.get("version") != VERSION:
        raise DvmError(f"unsupported version: {payload.get('version')!r}")
    raw_lines = payload.get("lines")
    if not isinstance(raw_lines, list):
        raise DvmError("missing document lines")
    lines: list[Line] = [[_node_from_json(node) for node in line] for line in raw_lines]
    return DvmDocument(
        lines=lines or [[]],
        language=str(payload.get("language", "en")),
        profile=payload.get("profile"),
    )
