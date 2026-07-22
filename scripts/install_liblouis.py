"""Download and install the liblouis native library and tables.

liblouis is not a plain pip install: it is a native library plus a tables
directory. This script fetches the official prebuilt package that matches
the platform and drops the library and tables into ``site-packages`` under
``disvimat_liblouis/`` so our adapter finds them automatically.

Usage::

    python scripts/install_liblouis.py

Only 64-bit Windows has a prebuilt package here; on Linux/macOS install
liblouis from your package manager (``apt install liblouis``,
``brew install liblouis``) and point ``LIBLOUIS_DLL`` / ``LOUIS_TABLEPATH``
at it. See docs/en/BRAILLE.md.
"""

from __future__ import annotations

import io
import shutil
import sys
import sysconfig
import urllib.request
import zipfile
from pathlib import Path

VERSION = "3.38.0"
WIN64_ZIP = (
    f"https://github.com/liblouis/liblouis/releases/download/v{VERSION}/"
    f"liblouis-{VERSION}-win64.zip"
)
INSTALL_SUBDIR = "disvimat_liblouis"


def _download(url: str) -> bytes:
    print(f"  downloading {url}")
    with urllib.request.urlopen(url) as response:  # noqa: S310 (trusted host)
        return bytes(response.read())


def main() -> int:
    if sys.platform != "win32" or sys.maxsize <= 2**32:
        print(
            "No prebuilt liblouis for this platform.\n"
            "Install it from your package manager and set LIBLOUIS_DLL and "
            "LOUIS_TABLEPATH; see docs/en/BRAILLE.md.",
            file=sys.stderr,
        )
        return 1

    target = Path(sysconfig.get_path("platlib")) / INSTALL_SUBDIR
    bin_dir = target / "bin"
    tables_dir = target / "tables"
    bin_dir.mkdir(parents=True, exist_ok=True)
    tables_dir.mkdir(parents=True, exist_ok=True)

    print(f"Installing liblouis into {target}")
    with zipfile.ZipFile(io.BytesIO(_download(WIN64_ZIP))) as archive:
        for member in archive.namelist():
            name = member.rsplit("/", 1)[-1]
            if member.endswith("bin/liblouis.dll"):
                (bin_dir / "liblouis.dll").write_bytes(archive.read(member))
            elif "share/liblouis/tables/" in member and name:
                (tables_dir / name).write_bytes(archive.read(member))

    count = len(list(tables_dir.iterdir()))
    if not (bin_dir / "liblouis.dll").is_file() or count == 0:
        shutil.rmtree(target, ignore_errors=True)
        print("Install failed: library or tables missing in the archive.", file=sys.stderr)
        return 1

    print("  verifying…")
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
    from disvimat.core.liblouis import load_native  # noqa: PLC0415

    native = load_native()
    braille = native.translate("es-g1.ctb", "Hola 123")
    print(f"  liblouis {native.version()} ready; {count} tables; 'Hola 123' -> {braille}")
    print("Done. The editor will use liblouis for text braille.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
