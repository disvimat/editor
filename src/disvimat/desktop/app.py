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
from disvimat.core.editor import Editor, Result, create_editor
from disvimat.core.filters.mathml import FilterError, MathMLFilter
from disvimat.core.output import BrailleProvider
from disvimat.core.tables import Catalog, data_dir
from disvimat.core.ui_text import UIText
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

    def __init__(self, editor: Editor, transcriber: BrailleProvider | None, text: UIText) -> None:
        super().__init__(None, title=text("app_title"))
        self._editor = editor
        self._transcriber = transcriber
        self._text = text
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
        result = self._editor.press(character)
        if result is None and (character.isalnum() or character == " "):
            result = self._editor.type_character(character)
        if result is not None:
            self._apply(result)
        else:
            event.Skip()

    def _apply(self, result: Result) -> None:
        self._document.ChangeValue(result.text)
        self._document.SetInsertionPoint(result.position)
        self.SetStatusText(result.speech)
        if self._braille is not None and self._braille.IsShown() and self._transcriber:
            self._braille.show_braille(self._transcriber.unicode(self._editor.document.root))

    # --- menu ----------------------------------------------------------------

    def _build_menu(self) -> None:
        text = self._text
        file_menu = wx.Menu()
        import_item = file_menu.Append(wx.ID_OPEN, text("menu_import_xhtml") + "\tCtrl+I")
        export_item = file_menu.Append(wx.ID_SAVEAS, text("menu_export_xhtml") + "\tCtrl+E")
        export_bra = file_menu.Append(wx.ID_ANY, text("menu_export_bra"))
        file_menu.AppendSeparator()
        quit_item = file_menu.Append(wx.ID_EXIT, text("menu_quit"))
        view_menu = wx.Menu()
        braille_item = view_menu.Append(wx.ID_ANY, text("menu_braille_window") + "\tCtrl+6")
        bar = wx.MenuBar()
        bar.Append(file_menu, text("menu_file"))
        bar.Append(view_menu, text("menu_view"))
        self.SetMenuBar(bar)
        self.Bind(wx.EVT_MENU, self._import, import_item)
        self.Bind(wx.EVT_MENU, self._export_xhtml, export_item)
        self.Bind(wx.EVT_MENU, self._export_bra, export_bra)
        self.Bind(wx.EVT_MENU, self._toggle_braille, braille_item)
        self.Bind(wx.EVT_MENU, lambda _event: self.Close(), quit_item)
        if self._transcriber is None:
            # No braille tables for this language: the features stay disabled.
            export_bra.Enable(False)
            braille_item.Enable(False)

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
        content = exporter.xhtml_document(self._editor.document.root)
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(content)
        self.SetStatusText(text("status_exported", path=path))

    def _export_bra(self, _event: wx.CommandEvent) -> None:
        if self._transcriber is None:
            return
        text = self._text
        dialog = wx.FileDialog(
            self,
            text("dialog_export_bra"),
            wildcard=text("filter_bra") + " (*.bra)|*.bra",
            style=wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT,
        )
        if dialog.ShowModal() != wx.ID_OK:
            return
        path = dialog.GetPath()
        content = self._transcriber.ascii(self._editor.document.root)
        with open(path, "w", encoding="ascii") as handle:
            handle.write(content + "\n")
        self.SetStatusText(text("status_exported", path=path))

    def _toggle_braille(self, _event: wx.CommandEvent) -> None:
        if self._transcriber is None:
            return
        if self._braille is None:
            self._braille = BrailleWindow(self, self._text)
        if self._braille.IsShown():
            self._braille.Hide()
            return
        self._braille.show_braille(self._transcriber.unicode(self._editor.document.root))
        self._braille.Show()
        self._document.SetFocus()


def main() -> None:
    language = os.environ.get("DISVIMAT_LANG", "en")
    profile = os.environ.get("DISVIMAT_PROFILE")
    catalog = Catalog.load(data_dir() / "elements.json")
    outputs = create_outputs(catalog, language)
    app = wx.App()
    window = EditorWindow(
        create_editor(language=language, profile=profile, reader=outputs.reader),
        outputs.braille,
        UIText.load(language=language),
    )
    window.Show()
    app.MainLoop()


if __name__ == "__main__":
    main()
