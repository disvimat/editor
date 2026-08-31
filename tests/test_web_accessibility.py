"""What the rendered page promises a screen reader.

These are the properties that, when they break, do not look broken: the
page still renders, the tests still pass, and the editor simply stops
being usable without sight. A duplicated id silently detaches a label; a
second live region turns every action into two announcements; a viewport
that forbids zoom locks out anyone who magnifies.

Structure is checked here, in Python, against the real rendered page. What
this cannot do is compute contrast or visibility, which needs a real
browser: an axe-core pass under a headless browser is still missing, and
is recorded as such in STATUS.md rather than faked here.
"""

from html.parser import HTMLParser

import pytest
from fastapi.testclient import TestClient

from disvimat.web.app import create_app


class Element:
    def __init__(self, tag: str, attributes: dict[str, str | None]) -> None:
        self.tag = tag
        self.attributes = attributes

    def get(self, name: str) -> str | None:
        return self.attributes.get(name)

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return f"<{self.tag} {self.attributes}>"


class Collector(HTMLParser):
    """Every start tag with its attributes, in document order."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.elements: list[Element] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.elements.append(Element(tag, dict(attrs)))

    handle_startendtag = handle_starttag  # type: ignore[assignment]


@pytest.fixture(scope="module")
def client() -> TestClient:
    return TestClient(create_app())


def parse(client: TestClient, query: str = "") -> list[Element]:
    page = client.get(f"/{query}").text
    collector = Collector()
    collector.feed(page)
    return collector.elements


@pytest.fixture(scope="module")
def elements(client: TestClient) -> list[Element]:
    return parse(client)


def ids(elements: list[Element]) -> list[str]:
    return [value for e in elements if (value := e.get("id")) is not None]


def find(elements: list[Element], **attributes: str) -> list[Element]:
    return [e for e in elements if all(e.get(k) == v for k, v in attributes.items())]


# --- announcements -----------------------------------------------------------


def test_there_is_exactly_one_live_region(elements: list[Element]) -> None:
    """Two would make the synthesiser say everything twice."""
    live = [e for e in elements if e.get("aria-live") is not None]
    assert len(live) == 1, f"expected one aria-live region, found {live}"
    assert live[0].get("id") == "announcement"
    assert live[0].get("aria-live") == "assertive"
    assert live[0].get("aria-atomic") == "true"


def test_the_status_bar_is_not_a_live_region(elements: list[Element]) -> None:
    """It shows the same message the live region announces, on purpose."""
    status = find(elements, id="status")
    assert status, "the status bar is missing"
    assert status[0].get("aria-live") is None, "the message would be spoken twice"


# --- the editing surface -----------------------------------------------------


def test_the_editor_is_focusable_and_named(elements: list[Element]) -> None:
    editor = find(elements, id="editor")
    assert editor, "the editing surface is missing"
    surface = editor[0]
    # role=application hands every key to the page, so it must carry its own
    # name and instructions: the screen reader will not narrate the page.
    assert surface.get("role") == "application"
    assert surface.get("tabindex") == "0"
    assert surface.get("aria-label"), "the editing surface has no accessible name"
    assert surface.get("aria-describedby"), "no instructions are pointed at"


def test_every_aria_reference_resolves(elements: list[Element]) -> None:
    """A reference to a missing id is silently dropped by the screen reader."""
    known = set(ids(elements))
    for element in elements:
        for attribute in ("aria-describedby", "aria-labelledby"):
            value = element.get(attribute)
            if value is None:
                continue
            missing = set(value.split()) - known
            assert not missing, f"{element.tag}[{attribute}] points at {missing}"


def test_ids_are_unique(elements: list[Element]) -> None:
    """A duplicate id detaches whatever pointed at the first one."""
    seen = ids(elements)
    duplicates = {value for value in seen if seen.count(value) > 1}
    assert not duplicates, f"duplicate ids: {duplicates}"


# --- getting around ----------------------------------------------------------


def test_the_skip_link_leads_somewhere(elements: list[Element]) -> None:
    links = [e for e in elements if e.tag == "a" and (e.get("href") or "").startswith("#")]
    assert links, "there is no skip link"
    target = (links[0].get("href") or "")[1:]
    assert target in ids(elements), f"the skip link points at a missing #{target}"


def test_there_is_one_first_level_heading(elements: list[Element]) -> None:
    assert len([e for e in elements if e.tag == "h1"]) == 1


def test_heading_levels_do_not_skip(elements: list[Element]) -> None:
    levels = [int(e.tag[1]) for e in elements if e.tag in {"h1", "h2", "h3", "h4"}]
    for previous, current in zip(levels, levels[1:], strict=False):
        assert current <= previous + 1, f"h{previous} is followed by h{current}"


def test_every_section_is_named(elements: list[Element]) -> None:
    for section in [e for e in elements if e.tag == "section"]:
        assert section.get("aria-labelledby") or section.get("aria-label"), (
            "a landmark with no name is just an unlabelled region"
        )


# --- zoom and language -------------------------------------------------------


def test_the_page_may_be_zoomed(elements: list[Element]) -> None:
    """Forbidding zoom locks out everyone who magnifies (WCAG 1.4.4)."""
    viewport = find(elements, name="viewport")
    assert viewport, "no viewport meta tag"
    content = (viewport[0].get("content") or "").replace(" ", "")
    assert "user-scalable=no" not in content
    assert "maximum-scale=1" not in content


@pytest.mark.parametrize("language", ["en", "es", "fr"])
def test_the_document_declares_the_language_it_speaks(client: TestClient, language: str) -> None:
    """A screen reader picks its voice from this."""
    elements = parse(client, f"?language={language}")
    html = [e for e in elements if e.tag == "html"]
    assert html and html[0].get("lang") == language


def test_the_file_inputs_are_labelled(elements: list[Element]) -> None:
    """They sit inside a <label>, so the accessible name comes from it."""
    files = [e for e in elements if e.tag == "input" and e.get("type") == "file"]
    assert files, "the import controls are missing"
    for control in files:
        assert control.get("id"), "a file input with no id cannot be pointed at"
