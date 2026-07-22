"""Download and install the MathCAT Python binding into this environment.

MathCAT is not on PyPI, but the project publishes prebuilt binaries (built
with PyO3 abi3, so one build serves every Python 3.x). This script fetches
the binary that matches the running interpreter plus MathCAT's ``Rules``
directory, and drops both into ``site-packages`` so
``import libmathcat_py`` and our adapter find them automatically.

Usage::

    python scripts/install_mathcat.py

When no prebuilt binary matches this platform, the script prints the
build-from-source instructions (see docs/en/MATHCAT.md) and exits.
"""

from __future__ import annotations

import io
import sys
import sysconfig
import urllib.request
import zipfile
from pathlib import Path

RELEASE = "https://github.com/daisy/MathCATForPython/releases/download/latest"
RULES_ZIP = f"{RELEASE}/Rules.zip"

#: Prebuilt binaries the release offers, keyed by (os, 64-bit?).
_BINARIES = {
    ("win32", True): "libmathcat_py-64-3.13-win.zip",
    ("linux", True): "libmathcat_py-64-3.13-linux.zip",
}


def _binary_asset() -> str | None:
    sixty_four = sys.maxsize > 2**32
    key = ("win32" if sys.platform == "win32" else "linux", sixty_four)
    return _BINARIES.get(key)


def _download(url: str) -> bytes:
    print(f"  downloading {url}")
    with urllib.request.urlopen(url) as response:  # noqa: S310 (trusted host)
        return bytes(response.read())


def main() -> int:
    target = Path(sysconfig.get_path("platlib"))
    asset = _binary_asset()
    if asset is None:
        print(
            "No prebuilt MathCAT binary matches this platform/interpreter.\n"
            "Build it from source (needs Rust): see docs/en/MATHCAT.md.",
            file=sys.stderr,
        )
        return 1

    print(f"Installing MathCAT into {target}")
    with zipfile.ZipFile(io.BytesIO(_download(f"{RELEASE}/{asset}"))) as archive:
        archive.extractall(target)
    with zipfile.ZipFile(io.BytesIO(_download(RULES_ZIP))) as archive:
        archive.extractall(target)  # yields a Rules/ folder next to the .pyd

    print("  verifying…")
    sys.path.insert(0, str(target))
    import libmathcat_py  # noqa: PLC0415

    rules = target / "Rules"
    libmathcat_py.SetRulesDir(str(rules))
    libmathcat_py.SetPreference("Language", "es")
    libmathcat_py.SetMathML("<math><mn>1</mn></math>")
    print(f"  MathCAT {libmathcat_py.GetVersion()} ready; rules at {rules}")
    print("Done. The editor will now use MathCAT for speech and braille.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
