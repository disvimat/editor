"""Tell what an unknown document file actually is.

Migrating users arrive with files from other editors (Lambda, EDICO…) whose
formats are not documented. Guessing wastes time and produces wrong
importers, so this answers the first question with evidence: is it text,
XML, a zip container, compressed, or encrypted?

Run it on a file::

    python -m disvimat.tools.format_probe path/to/document.lambda

The verdict drives what happens next: readable text or XML can be parsed
into a filter; a container can be unpacked; **encrypted content cannot be
imported at all**, and the honest answer is to ask the vendor for an
export instead of trying to break it.
"""

import bz2
import collections
import io
import lzma
import math
import sys
import zipfile
import zlib
from dataclasses import dataclass, field
from pathlib import Path

#: Leading bytes that identify a container or compression format.
SIGNATURES: dict[bytes, str] = {
    b"PK\x03\x04": "ZIP container (may hold XML parts)",
    b"\x1f\x8b": "gzip",
    b"BZh": "bzip2",
    b"\xfd7zXZ": "xz",
    b"Rar!": "RAR",
    b"%PDF": "PDF",
    b"{\\rtf": "RTF",
    b"\xd0\xcf\x11\xe0": "OLE compound file (old Office)",
    b"<?xml": "XML",
    b"\xef\xbb\xbf": "UTF-8 text (with BOM)",
    b"\xff\xfe": "UTF-16 LE text",
    b"\xfe\xff": "UTF-16 BE text",
}

#: Above this entropy the content carries no exploitable structure.
ENCRYPTED_ENTROPY = 7.9


@dataclass
class Report:
    """What the probe found, and what it means for importing."""

    path: Path
    size: int
    header: str
    signature: str | None
    entropy: float
    printable_ratio: float
    verdict: str
    detail: list[str] = field(default_factory=list)

    def render(self) -> str:
        lines = [
            f"file      : {self.path.name}  ({self.size} bytes)",
            f"header    : {self.header}",
            f"signature : {self.signature or 'none known'}",
            f"entropy   : {self.entropy:.3f} bits/byte  (8.0 = random)",
            f"printable : {self.printable_ratio:.0%}",
            f"VERDICT   : {self.verdict}",
        ]
        lines.extend(f"  - {note}" for note in self.detail)
        return "\n".join(lines)


def _entropy(data: bytes) -> float:
    if not data:
        return 0.0
    counts = collections.Counter(data)
    return -sum((count / len(data)) * math.log2(count / len(data)) for count in counts.values())


def _decompresses(data: bytes) -> str | None:
    attempts = {
        "zlib": zlib.decompress,
        "gzip": lambda raw: zlib.decompress(raw, 16 + zlib.MAX_WBITS),
        "raw deflate": lambda raw: zlib.decompress(raw, -zlib.MAX_WBITS),
        "bzip2": bz2.decompress,
        "xz/lzma": lzma.decompress,
    }
    for name, decompress in attempts.items():
        try:
            decompress(data)
        except Exception:  # noqa: BLE001, S112 - probing on purpose
            continue
        return name
    return None


def _as_text(data: bytes) -> str | None:
    for encoding in ("utf-8-sig", "utf-16", "cp1252"):
        try:
            return data.decode(encoding)
        except (UnicodeDecodeError, LookupError):
            continue
    return None


def probe(data: bytes, path: Path | None = None) -> Report:
    """Inspect the bytes of a document and say what can be done with it."""
    path = path or Path("<bytes>")
    entropy = _entropy(data)
    printable = sum(1 for byte in data if 0x20 <= byte < 0x7F or byte in (9, 10, 13))
    ratio = printable / len(data) if data else 0.0
    signature = next((name for magic, name in SIGNATURES.items() if data.startswith(magic)), None)
    detail: list[str] = []

    if signature and signature.startswith("ZIP"):
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            names = archive.namelist()[:10]
        detail.append(f"parts: {', '.join(names)}")
        verdict = "container — unpack it and probe the parts"
    elif (compression := _decompresses(data)) is not None:
        detail.append(f"decompresses with {compression}")
        verdict = "compressed — decompress, then probe the result"
    elif (text := _as_text(data)) is not None and ratio > 0.7:
        stripped = text.lstrip()
        if stripped.startswith("<"):
            verdict = "XML/HTML text — a filter can parse it directly"
            if "MathML" in text or "<math" in text:
                detail.append("contains MathML: our existing importer already reads it")
        elif stripped.startswith("{"):
            verdict = "JSON text — a filter can parse it directly"
        else:
            verdict = "plain text — readable, a filter can parse it"
        detail.append(f"first line: {stripped.splitlines()[0][:70]!r}" if stripped else "")
    elif entropy >= ENCRYPTED_ENTROPY:
        verdict = "encrypted or strongly compressed — NOT importable as is"
        if len(data) % 16 == 0:
            detail.append("size is a multiple of 16: consistent with a block cipher")
        detail.append("ask the vendor for an export (MathML, XHTML) instead")
    else:
        verdict = "unknown binary — structured, worth reverse-engineering"
        detail.append(f"distinct byte values: {len(set(data))} of 256")

    return Report(
        path=path,
        size=len(data),
        header=data[:16].hex(" "),
        signature=signature,
        entropy=entropy,
        printable_ratio=ratio,
        verdict=verdict,
        detail=[note for note in detail if note],
    )


def probe_file(path: Path) -> Report:
    return probe(path.read_bytes(), path)


def main(argv: list[str] | None = None) -> int:
    arguments = sys.argv[1:] if argv is None else argv
    if not arguments:
        print(__doc__, file=sys.stderr)
        return 2
    for name in arguments:
        path = Path(name)
        if not path.is_file():
            print(f"not a file: {path}", file=sys.stderr)
            return 1
        print(probe_file(path).render())
        print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
