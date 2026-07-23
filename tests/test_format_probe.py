"""The format probe: deciding what a migrating user's file actually is.

Files from other editors arrive without documentation. Guessing produces
wrong importers, so the probe answers with evidence before any filter is
written — and says plainly when a file is encrypted and cannot be imported.
"""

import io
import zipfile
import zlib

from disvimat.tools.format_probe import probe


def test_xml_with_mathml_is_recognised_as_importable() -> None:
    data = (
        b'<?xml version="1.0"?><html><body><math '
        b'xmlns="http://www.w3.org/1998/Math/MathML"><mn>1</mn></math></body></html>'
    )
    report = probe(data)
    assert "XML" in report.verdict
    assert any("MathML" in note for note in report.detail)


def test_plain_text_is_readable() -> None:
    report = probe(b"frac(1,2) + raiz(3)")
    assert "plain text" in report.verdict


def test_json_is_recognised() -> None:
    report = probe(b'{"format": "disvimat-document", "lines": []}')
    assert "JSON" in report.verdict


def test_zip_container_lists_its_parts() -> None:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("content.xml", "<x/>")
    report = probe(buffer.getvalue())
    assert "container" in report.verdict
    assert any("content.xml" in note for note in report.detail)


def test_compressed_content_is_recognised() -> None:
    report = probe(zlib.compress(b"some readable content " * 40))
    assert "compressed" in report.verdict


def test_encrypted_content_is_refused_not_guessed() -> None:
    """High-entropy, block-aligned data must be reported as unimportable."""
    import secrets

    report = probe(secrets.token_bytes(4096))  # 4096 is a multiple of 16
    assert "encrypted" in report.verdict
    assert any("block cipher" in note for note in report.detail)
    assert any("export" in note for note in report.detail)


def test_report_renders_the_evidence() -> None:
    rendered = probe(b"hello world").render()
    assert "entropy" in rendered
    assert "VERDICT" in rendered
