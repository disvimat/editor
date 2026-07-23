"""Main editor window (presentation module B4, desktop).

The window is deliberately thin: it normalises key strokes into the
canonical table format, hands them to the core :class:`Editor` and
reflects the result in a native text control (which NVDA reads as the
caret moves) and in the status line. Interface strings come from the
``ui`` table; everything else is localised in the other tables.
"""

import os

import wx

from disvimat.backends import create_outputs
from disvimat.core.dvm import DvmError, from_dvm, to_dvm
from disvimat.core.editor import Editor, Result, create_editor
from disvimat.core.filters.mathml import FilterError, MathMLFilter
from disvimat.core.output import BrailleProvider
from disvimat.core.tables import Catalog, data_dir
from disvimat.core.ui_text import UIText
from disvimat.desktop.screen_reader import SpeechOutput, create_output
from disvimat.export.xhtml import XHTMLExporter

#: Special keys -> canonical table name.
_SPECIAL_KEYS = {
    wx.WXK_LEFT: "Left",
    wx.WXK_RIGHT: "Right",
    wx.WXK_UP: "Up",
    wx.WXK_DOWN: "Down",
    wx.WXK_HOME: "Home",
    wx.WXK_END: "End",
    wx.WXK_TAB: "Tab",
    wx.WXK_DELETE: "Delete",
    wx.WXK_BACK: "Backspace",
    wx.WXK_RETURN: "Return",
    wx.WXK_NUMPAD_ENTER: "Return",
    wx.WXK_NUMPAD_ADD: "NumAdd",
    wx.WXK_NUMPAD_SUBTRACT: "NumSubtract",
    wx.WXK_NUMPAD_MULTIPLY: "NumMultiply",
    wx.WXK_NUMPAD_DIVIDE: "NumDivide",
}


def _finished_word(result: Result) -> str:
    """The word the user has just closed with a space, if any.

    Screen readers announce typed characters but not the word being
    completed, which is what a writer wants to hear when pressing space.
    """
    before = result.text[: result.position].rstrip()
    if not before:
        return ""
    return before.split()[-1]


def canonical_keys(event: wx.KeyEvent) -> str | None:
    """The key stroke in canonical form ("Left", "Ctrl+F"), or None.

    Returns None for plain characters without modifiers: those arrive
    already translated by the keyboard layout in EVT_CHAR.
    """
    modifiers = []
    if event.ControlDown():
        modifiers.append("Ctrl")
    if event.AltDown():
        modifiers.append("Alt")
    if event.ShiftDown():
        modifiers.append("Shift")
    code = event.GetKeyCode()
    if code in _SPECIAL_KEYS:
        name = _SPECIAL_KEYS[code]
    elif modifiers and modifiers != ["Shift"]:
        unicode_key = event.GetUnicodeKey()
        if unicode_key == wx.WXK_NONE:
            return None
        name = chr(unicode_key)
    else:
        return None
    return "+".join([*modifiers, name]) if modifiers else name


class BrailleWindow(wx.Frame):
    """External window holding the braille transcription (B6)."""

    def __init__(self, parent: wx.Frame, text: UIText) -> None:
        super().__init__(parent, title=text("braille_window_title"))
        self._text = wx.TextCtrl(self, style=wx.TE_MULTILINE | wx.TE_READONLY)
        self._text.SetName(text("braille"))
        self.SetSize((700, 200))

    def show_braille(self, content: str) -> None:
        self._text.ChangeValue(content)


class EditorWindow(wx.Frame):
    """The accessible linear editor window."""

    def __init__(
        self,
        editor: Editor,
        transcriber: BrailleProvider | None,
        text: UIText,
        *,
        language: str = "en",
        profile: str | None = None,
        speech_backend: str = "tables",
        braille_backend: str = "none",
        speech: SpeechOutput | None = None,
    ) -> None:
        super().__init__(None, title=text("app_title"))
        self._editor = editor
        self._transcriber = transcriber
        self._text = text
        self._language = language
        self._profile = profile
        # The screen reader does not read the status bar by itself, so every
        # action is spoken here as well as shown.
        self._speech: SpeechOutput = speech if speech is not None else create_output()
        self._speech_backend = speech_backend
        self._braille_backend = braille_backend
        self._braille: BrailleWindow | None = None
        panel = wx.Panel(self)
        self._document = wx.TextCtrl(panel, style=wx.TE_MULTILINE | wx.TE_READONLY)
        self._document.SetName(text("document"))
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(self._document, 1, wx.EXPAND | wx.ALL, 4)
        panel.SetSizer(sizer)
        self.CreateStatusBar()
        self._build_menu()
        self.Bind(wx.EVT_CHAR_HOOK, self._on_key)
        self._document.Bind(wx.EVT_CHAR, self._on_character)
        self._document.SetFocus()
        self.SetSize((900, 400))

    # --- input ---------------------------------------------------------------

    def _on_key(self, event: wx.KeyEvent) -> None:
        keys = canonical_keys(event)
        if keys is not None:
            result = self._editor.press(keys)
            if result is not None:
                self._apply(result)
                return
        event.Skip()

    def _on_character(self, event: wx.KeyEvent) -> None:
        code = event.GetUnicodeKey()
        if code == wx.WXK_NONE:
            event.Skip()
            return
        character = chr(code)
        # The second stroke of a chord ("Ctrl+G, P") is a bare letter that
        # would otherwise be typed. While a chord waits, route it as a key
        # stroke (bindings name letters in upper case) instead of inserting it.
        if self._editor.chord_pending():
            completed = self._editor.press(character.upper())
            if completed is not None:
                self._apply(completed)
                return
        result = self._editor.press(character)
        if result is not None:  # an assigned sign or structure
            self._apply(result)
            return
        if character.isalnum() or character == " ":
            typed = self._editor.type_character(character)
            # The screen reader echoes typed characters itself, so repeating
            # them would double up. What it cannot know is the word the user
            # has just finished, which is announced when space closes it.
            self._apply(typed, speak=_finished_word(typed) if character == " " else "")
            return
        event.Skip()

    def _apply(self, result: Result, *, speak: str | None = None) -> None:
        """Reflect a result. ``speak`` overrides the spoken text ("" silences)."""
        self._document.ChangeValue(result.text)
        self._document.SetInsertionPoint(result.position)
        self.SetStatusText(result.speech)
        spoken = result.speech if speak is None else speak
        if spoken:
            self._speech.speak(spoken)
        if self._braille is not None and self._braille.IsShown() and self._transcriber:
            self._braille.show_braille(self._braille_text())
        if self._transcriber is not None:
            # Also push the current line to a connected braille display.
            self._speech.braille(self._transcriber.unicode(self._editor.document.current_line()))

    def _braille_text(self) -> str:
        """Braille of the whole document, one line per document line."""
        assert self._transcriber is not None
        return "\n".join(self._transcriber.unicode(line) for line in self._editor.document.lines)

    # --- menu ----------------------------------------------------------------

    def _build_menu(self) -> None:
        text = self._text
        bar = wx.MenuBar()

        file_menu = wx.Menu()
        new_item = file_menu.Append(wx.ID_NEW, text("menu_new") + "\tCtrl+N")
        open_item = file_menu.Append(wx.ID_OPEN, text("menu_open") + "\tCtrl+O")
        save_item = file_menu.Append(wx.ID_SAVE, text("menu_save") + "\tCtrl+S")
        file_menu.AppendSeparator()
        import_item = file_menu.Append(wx.ID_ANY, text("menu_import_xhtml") + "\tCtrl+I")
        export_item = file_menu.Append(wx.ID_ANY, text("menu_export_xhtml") + "\tCtrl+E")
        export_braille = file_menu.Append(wx.ID_ANY, text("menu_export_braille"))
        file_menu.AppendSeparator()
        quit_item = file_menu.Append(wx.ID_EXIT, text("menu_quit"))
        bar.Append(file_menu, text("menu_file"))
        self.Bind(wx.EVT_MENU, self._new, new_item)
        self.Bind(wx.EVT_MENU, self._open_dvm, open_item)
        self.Bind(wx.EVT_MENU, self._save_dvm, save_item)
        self.Bind(wx.EVT_MENU, self._import, import_item)
        self.Bind(wx.EVT_MENU, self._export_xhtml, export_item)
        self.Bind(wx.EVT_MENU, self._export_braille, export_braille)
        self.Bind(wx.EVT_MENU, lambda _event: self.Close(), quit_item)

        # Edit, Insert and Tools items all run an editor command by its
        # canonical key stroke, so the menus and the shortcuts never diverge.
        edit_menu = wx.Menu()
        self._add_command(edit_menu, "menu_undo", "Ctrl+Z")
        self._add_command(edit_menu, "menu_redo", "Ctrl+Y")
        bar.Append(edit_menu, text("menu_edit"))

        insert_menu = wx.Menu()
        self._add_command(insert_menu, "menu_insert_fraction", "Ctrl+F")
        self._add_command(insert_menu, "menu_insert_sqrt", "Ctrl+R")
        self._add_command(insert_menu, "menu_insert_power", "Ctrl+P")
        bar.Append(insert_menu, text("menu_insert"))

        tools_menu = wx.Menu()
        self._add_command(tools_menu, "menu_calculate", "Ctrl+Return")
        self._add_command(tools_menu, "menu_read_line", "Ctrl+Shift+L")
        bar.Append(tools_menu, text("menu_tools"))

        view_menu = wx.Menu()
        braille_item = view_menu.Append(wx.ID_ANY, text("menu_braille_window") + "\tCtrl+6")
        bar.Append(view_menu, text("menu_view"))
        self.Bind(wx.EVT_MENU, self._toggle_braille, braille_item)

        help_menu = wx.Menu()
        about_item = help_menu.Append(wx.ID_ABOUT, text("menu_about"))
        bar.Append(help_menu, text("menu_help"))
        self.Bind(wx.EVT_MENU, self._about, about_item)

        self.SetMenuBar(bar)
        if self._transcriber is None:
            # No braille source for this language: the features stay disabled.
            export_braille.Enable(False)
            braille_item.Enable(False)

    def _add_command(self, menu: wx.Menu, label_id: str, keys: str) -> None:
        """Add a menu item that runs the editor command bound to ``keys``."""
        item = menu.Append(wx.ID_ANY, self._text(label_id) + f"\t{keys}")
        self.Bind(wx.EVT_MENU, lambda _event, k=keys: self._run(k), item)

    def _run(self, keys: str) -> None:
        result = self._editor.press(keys)
        if result is not None:
            self._apply(result)
        self._document.SetFocus()

    def _new(self, _event: wx.CommandEvent) -> None:
        self._apply(self._editor.load_lines([[]]))
        self._document.SetFocus()

    def _open_dvm(self, _event: wx.CommandEvent) -> None:
        text = self._text
        dialog = wx.FileDialog(
            self,
            text("dialog_open"),
            wildcard=text("filter_dvm") + " (*.dvm)|*.dvm",
            style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST,
        )
        if dialog.ShowModal() != wx.ID_OK:
            return
        path = dialog.GetPath()
        try:
            with open(path, encoding="utf-8") as handle:
                document = from_dvm(handle.read())
        except (OSError, DvmError) as error:
            wx.MessageBox(str(error), text("error_open"), wx.ICON_ERROR)
            return
        self._apply(self._editor.load_lines(document.lines))
        self._document.SetFocus()

    def _save_dvm(self, _event: wx.CommandEvent) -> None:
        text = self._text
        dialog = wx.FileDialog(
            self,
            text("dialog_save"),
            wildcard=text("filter_dvm") + " (*.dvm)|*.dvm",
            style=wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT,
        )
        if dialog.ShowModal() != wx.ID_OK:
            return
        path = dialog.GetPath()
        content = to_dvm(
            self._editor.document.lines, language=self._language, profile=self._profile
        )
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(content)
        self.SetStatusText(text("status_exported", path=path))

    def _about(self, _event: wx.CommandEvent) -> None:
        from disvimat import __version__

        body = self._text(
            "about_body",
            version=__version__,
            speech=self._speech_backend,
            braille=self._braille_backend,
        )
        wx.MessageBox(body, self._text("menu_about"), wx.ICON_INFORMATION)

    def _import(self, _event: wx.CommandEvent) -> None:
        text = self._text
        dialog = wx.FileDialog(
            self,
            text("dialog_import"),
            wildcard=text("filter_xhtml") + " (*.xhtml;*.html;*.xml)|*.xhtml;*.html;*.xml",
            style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST,
        )
        if dialog.ShowModal() != wx.ID_OK:
            return
        path = dialog.GetPath()
        try:
            with open(path, encoding="utf-8") as handle:
                content = handle.read()
            nodes = MathMLFilter(self._editor.catalog).from_xhtml(content)
        except (OSError, FilterError) as error:
            wx.MessageBox(str(error), text("error_import"), wx.ICON_ERROR)
            return
        self._apply(self._editor.load(nodes))

    def _export_xhtml(self, _event: wx.CommandEvent) -> None:
        text = self._text
        dialog = wx.FileDialog(
            self,
            text("dialog_export_xhtml"),
            wildcard=text("filter_xhtml") + " (*.xhtml)|*.xhtml",
            style=wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT,
        )
        if dialog.ShowModal() != wx.ID_OK:
            return
        path = dialog.GetPath()
        exporter = XHTMLExporter(self._editor.catalog)
        content = exporter.xhtml_document_lines(
            self._editor.document.lines, language=self._language
        )
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(content)
        self.SetStatusText(text("status_exported", path=path))

    def _export_braille(self, _event: wx.CommandEvent) -> None:
        if self._transcriber is None:
            return
        text = self._text
        dialog = wx.FileDialog(
            self,
            text("dialog_export_braille"),
            wildcard=text("filter_braille") + " (*.brl)|*.brl",
            style=wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT,
        )
        if dialog.ShowModal() != wx.ID_OK:
            return
        path = dialog.GetPath()
        # Unicode braille (U+2800…), UTF-8: the modern, portable form.
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(self._braille_text() + "\n")
        self.SetStatusText(text("status_exported", path=path))

    def _toggle_braille(self, _event: wx.CommandEvent) -> None:
        if self._transcriber is None:
            return
        if self._braille is None:
            self._braille = BrailleWindow(self, self._text)
        if self._braille.IsShown():
            self._braille.Hide()
            return
        self._braille.show_braille(self._braille_text())
        self._braille.Show()
        self._document.SetFocus()


def main() -> None:
    language = os.environ.get("DISVIMAT_LANG", "en")
    profile = os.environ.get("DISVIMAT_PROFILE")
    keymap = os.environ.get("DISVIMAT_KEYMAP")
    catalog = Catalog.load(data_dir() / "elements.json")
    outputs = create_outputs(catalog, language)
    app = wx.App()
    window = EditorWindow(
        create_editor(language=language, profile=profile, reader=outputs.reader, keymap=keymap),
        outputs.braille,
        UIText.load(language=language),
        language=language,
        profile=profile,
        speech_backend=outputs.speech_backend,
        braille_backend=outputs.braille_backend,
    )
    window.Show()
    app.MainLoop()


if __name__ == "__main__":
    main()
