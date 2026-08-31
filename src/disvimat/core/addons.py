"""Add-ons: extending the editor without touching the core (module A5).

An add-on is ordinary Python that registers what it contributes. It can
add **commands** (a key stroke, a spoken label per language and the code
to run) and **exporters**, and the editor wires them in as if they were
built in — same key resolution, same speech, same undo.

Writing one is small::

    def register(registry):
        registry.add_command(
            id="shout",
            keys="Ctrl+Alt+S",
            labels={"en": "shout", "es": "gritar"},
            run=lambda editor: editor.document.current_line() and "shouted",
        )

DISVIMAT finds add-ons two ways:

- **Installed packages** that declare the ``disvimat.addons`` entry point,
  which is the normal way to distribute one.
- **A folder** of plain ``.py`` files pointed at by ``DISVIMAT_ADDONS``,
  which is the quick way for a teacher or a user to script an action —
  the "script designer" the original brief asked for.

A broken add-on must never take the editor down: loading and running are
both contained, and failures are collected in :attr:`Registry.errors` for
the interface to report.
"""

import importlib.util
import os
import sys
from dataclasses import dataclass, field
from importlib import metadata
from pathlib import Path
from typing import TYPE_CHECKING, Protocol

from disvimat.core.document import Line
from disvimat.core.elements import Element, ElementType
from disvimat.core.tables import KeyEntry, LabelEntry

if TYPE_CHECKING:  # pragma: no cover - typing only, avoids a circular import
    from disvimat.core.editor import Editor

#: Entry point group an installed add-on declares in its pyproject.
ENTRY_POINT_GROUP = "disvimat.addons"

#: Environment variable holding a folder of loose ``.py`` add-ons.
ADDON_PATH_ENV = "DISVIMAT_ADDONS"

#: Set this to skip automatic discovery. The test suite sets it so results
#: do not depend on what happens to be installed on the machine.
DISABLE_ENV = "DISVIMAT_NO_ADDONS"

#: Category given to elements contributed by add-ons.
ADDON_CATEGORY = "addon"

#: Message id used when an add-on command raises (see the messages table).
MSG_ADDON_FAILED = "addon_failed"


class CommandFunction(Protocol):
    """What an add-on command does; returns the text to speak."""

    def __call__(self, editor: "Editor") -> str: ...


class ExportFunction(Protocol):
    """Turns the document lines into the text of an exported file."""

    def __call__(self, lines: list[Line]) -> str: ...


@dataclass(frozen=True)
class AddonCommand:
    """A command an add-on contributes, ready to be wired in."""

    id: str
    keys: str | None
    labels: dict[str, str]
    run: CommandFunction

    def label(self, language: str) -> str:
        """The label for a language, falling back to English then the id."""
        return self.labels.get(language) or self.labels.get("en") or self.id


@dataclass(frozen=True)
class AddonExporter:
    """An export format an add-on contributes."""

    id: str
    extension: str
    labels: dict[str, str]
    dump: ExportFunction

    def label(self, language: str) -> str:
        return self.labels.get(language) or self.labels.get("en") or self.id


@dataclass
class Registry:
    """What add-ons have contributed, and what went wrong loading them."""

    commands: dict[str, AddonCommand] = field(default_factory=dict)
    exporters: dict[str, AddonExporter] = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)

    # --- the API add-ons call ------------------------------------------------

    def add_command(
        self,
        id: str,  # noqa: A002 - matches the catalogue vocabulary
        run: CommandFunction,
        *,
        keys: str | None = None,
        labels: dict[str, str] | None = None,
    ) -> None:
        """Contribute a command, optionally bound to a key stroke."""
        if id in self.commands:
            raise ValueError(f"duplicate add-on command: {id!r}")
        self.commands[id] = AddonCommand(id, keys, labels or {}, run)

    def add_exporter(
        self,
        id: str,  # noqa: A002
        extension: str,
        dump: ExportFunction,
        *,
        labels: dict[str, str] | None = None,
    ) -> None:
        """Contribute an export format (``extension`` like ``".tex"``)."""
        if id in self.exporters:
            raise ValueError(f"duplicate add-on exporter: {id!r}")
        self.exporters[id] = AddonExporter(id, extension, labels or {}, dump)

    # --- what the editor consumes --------------------------------------------

    def elements(self) -> list[Element]:
        """Catalogue entries for the contributed commands."""
        return [
            Element(id=command.id, type=ElementType.COMMAND, category=ADDON_CATEGORY)
            for command in self.commands.values()
        ]

    def key_entries(self) -> list[KeyEntry]:
        """Key bindings for the commands that asked for one."""
        return [
            KeyEntry(id=command.id, keys=command.keys)
            for command in self.commands.values()
            if command.keys
        ]

    def label_entries(self, language: str) -> list[LabelEntry]:
        """Speech labels for the contributed commands, in one language."""
        return [
            LabelEntry(id=command.id, label=command.label(language))
            for command in self.commands.values()
        ]


def _register_from(module: object, registry: Registry, source: str) -> None:
    register = getattr(module, "register", None)
    if register is None:
        registry.errors.append(f"{source}: no register() function")
        return
    try:
        register(registry)
    except Exception as error:  # noqa: BLE001 - one bad add-on must not stop the rest
        registry.errors.append(f"{source}: {error}")


def _load_entry_points(registry: Registry) -> None:
    try:
        found = metadata.entry_points(group=ENTRY_POINT_GROUP)
    except Exception as error:  # noqa: BLE001
        registry.errors.append(f"entry points: {error}")
        return
    for entry in found:
        try:
            loaded = entry.load()
        except Exception as error:  # noqa: BLE001
            registry.errors.append(f"{entry.name}: {error}")
            continue
        if callable(loaded) and not hasattr(loaded, "register"):
            try:
                loaded(registry)
            except Exception as error:  # noqa: BLE001
                registry.errors.append(f"{entry.name}: {error}")
        else:
            _register_from(loaded, registry, entry.name)


def _load_folder(folder: Path, registry: Registry) -> None:
    for path in sorted(folder.glob("*.py")):
        if path.name.startswith("_"):
            continue
        spec = importlib.util.spec_from_file_location(f"disvimat_addon_{path.stem}", path)
        if spec is None or spec.loader is None:
            registry.errors.append(f"{path.name}: cannot be loaded")
            continue
        module = importlib.util.module_from_spec(spec)
        try:
            sys.modules[spec.name] = module
            spec.loader.exec_module(module)
        except Exception as error:  # noqa: BLE001
            registry.errors.append(f"{path.name}: {error}")
            continue
        _register_from(module, registry, path.name)


def load_addons(folder: Path | None = None, *, entry_points: bool = True) -> Registry:
    """Discover add-ons and return what they contributed.

    ``folder`` overrides the ``DISVIMAT_ADDONS`` directory; set
    ``entry_points`` to False to load only the folder (what tests do).
    """
    registry = Registry()
    # The switch turns off *discovery*; an explicitly given folder always
    # loads, which is how the tests exercise the loader.
    discovering = folder is None
    if discovering and os.environ.get(DISABLE_ENV):
        return registry
    if entry_points:
        _load_entry_points(registry)
    if discovering:
        from_environment = os.environ.get(ADDON_PATH_ENV)
        folder = Path(from_environment) if from_environment else None
    if folder is not None and folder.is_dir():
        _load_folder(folder, registry)
    return registry
