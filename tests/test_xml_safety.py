"""Imported XML is untrusted input, and parsing it is a security boundary.

A document reaches the filter from outside: a web request, or a file a
desktop user was sent by someone else. These tests pin the guarantees of
:func:`disvimat.core.filters.mathml._parse` so that a future change to the
parser cannot quietly reopen the hole.
"""

from pathlib import Path

import pytest

from disvimat.core.filters.mathml import FilterError, MathMLFilter
from disvimat.core.tables import Catalog

DATA = Path(__file__).resolve().parents[1] / "data"

#: A small document that would expand to roughly 300 KB of text; adding two
#: more levels reaches gigabytes and exhausts the memory of whoever parses it.
BILLION_LAUGHS = """<?xml version="1.0"?><!DOCTYPE lolz [
<!ENTITY lol "lol">
<!ENTITY lol1 "&lol;&lol;&lol;&lol;&lol;&lol;&lol;&lol;&lol;&lol;">
<!ENTITY lol2 "&lol1;&lol1;&lol1;&lol1;&lol1;&lol1;&lol1;&lol1;&lol1;&lol1;">
<!ENTITY lol3 "&lol2;&lol2;&lol2;&lol2;&lol2;&lol2;&lol2;&lol2;&lol2;&lol2;">
<!ENTITY lol4 "&lol3;&lol3;&lol3;&lol3;&lol3;&lol3;&lol3;&lol3;&lol3;&lol3;">
<!ENTITY lol5 "&lol4;&lol4;&lol4;&lol4;&lol4;&lol4;&lol4;&lol4;&lol4;&lol4;">
]><math><mi>&lol5;</mi></math>"""


@pytest.fixture
def filter_() -> MathMLFilter:
    return MathMLFilter(Catalog.load(DATA / "elements.json"))


def test_entity_expansion_bomb_is_refused(filter_: MathMLFilter) -> None:
    """The "billion laughs" denial of service must not parse."""
    with pytest.raises(FilterError, match="entity declarations"):
        filter_.from_xhtml(BILLION_LAUGHS)


def test_local_file_disclosure_is_refused(filter_: MathMLFilter) -> None:
    """An external entity must never make the parser read a local file."""
    attack = '<!DOCTYPE r [<!ENTITY x SYSTEM "file:///etc/passwd">]><math><mi>&x;</mi></math>'
    with pytest.raises(FilterError):
        filter_.from_xhtml(attack)


def test_remote_fetch_is_refused(filter_: MathMLFilter) -> None:
    """Nor may it call out to a URL of the attacker's choosing."""
    attack = '<!DOCTYPE r [<!ENTITY x SYSTEM "http://example.invalid/x">]><math><mi>&x;</mi></math>'
    with pytest.raises(FilterError):
        filter_.from_xhtml(attack)


def test_a_plain_doctype_still_works(filter_: MathMLFilter) -> None:
    """Refusing entities must not refuse real XHTML, which carries a DOCTYPE."""
    document = (
        "<!DOCTYPE html>"
        '<html xmlns="http://www.w3.org/1999/xhtml"><body>'
        '<math xmlns="http://www.w3.org/1998/Math/MathML">'
        "<mfrac><mn>2</mn><mn>3</mn></mfrac></math></body></html>"
    )
    assert len(filter_.from_xhtml(document)) == 1


def test_namespaced_and_plain_documents_agree(filter_: MathMLFilter) -> None:
    """Driving expat directly must keep namespace handling intact."""
    plain = filter_.from_text("<math><mfrac><mn>2</mn><mn>3</mn></mfrac></math>")
    namespaced = filter_.from_text(
        '<math xmlns="http://www.w3.org/1998/Math/MathML">'
        "<mfrac><mn>2</mn><mn>3</mn></mfrac></math>"
    )
    assert len(plain) == len(namespaced) == 1


def test_malformed_xml_is_still_reported_clearly(filter_: MathMLFilter) -> None:
    with pytest.raises(FilterError, match="malformed MathML"):
        filter_.from_text("<math><mn>1</mn>")
