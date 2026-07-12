"""Ventana principal del editor (módulo de presentación B4, escritorio).

La ventana es deliberadamente delgada: normaliza las pulsaciones al
formato canónico de las tablas, se las pasa al :class:`Editor` del
núcleo y refleja el resultado en un control de texto nativo (que NVDA
lee al mover el caret) y en la línea de estado. Las cadenas propias de
la interfaz pasan por gettext (:mod:`disvimat.core.i18n`); todo lo
demás se localiza en las tablas por lengua.
"""

import os

import wx

from disvimat.core.editor import Editor, Resultado, crear_editor
from disvimat.core.filtros.mathml import ErrorDeFiltro, FiltroMathML
from disvimat.core.i18n import _, instalar
from disvimat.core.transcripcion.braille import Transcriptor, crear_transcriptor
from disvimat.export.xhtml import ExportadorXHTML

#: Teclas especiales -> nombre canónico de las tablas.
_ESPECIALES = {
    wx.WXK_LEFT: "Left",
    wx.WXK_RIGHT: "Right",
    wx.WXK_UP: "Up",
    wx.WXK_DOWN: "Down",
    wx.WXK_HOME: "Home",
    wx.WXK_END: "End",
    wx.WXK_TAB: "Tab",
    wx.WXK_DELETE: "Delete",
    wx.WXK_BACK: "Backspace",
    wx.WXK_NUMPAD_ADD: "NumAdd",
    wx.WXK_NUMPAD_SUBTRACT: "NumSubtract",
    wx.WXK_NUMPAD_MULTIPLY: "NumMultiply",
    wx.WXK_NUMPAD_DIVIDE: "NumDivide",
}


def tecla_canonica(evento: wx.KeyEvent) -> str | None:
    """Pulsación en formato canónico ("Left", "Ctrl+F"), o None.

    Devuelve None para los caracteres sin modificadores: esos llegan ya
    traducidos por el teclado en EVT_CHAR y se tratan allí.
    """
    modificadores = []
    if evento.ControlDown():
        modificadores.append("Ctrl")
    if evento.AltDown():
        modificadores.append("Alt")
    if evento.ShiftDown():
        modificadores.append("Shift")
    codigo = evento.GetKeyCode()
    if codigo in _ESPECIALES:
        nombre = _ESPECIALES[codigo]
    elif modificadores and modificadores != ["Shift"]:
        unicode_ = evento.GetUnicodeKey()
        if unicode_ == wx.WXK_NONE:
            return None
        nombre = chr(unicode_)
    else:
        return None
    return "+".join([*modificadores, nombre]) if modificadores else nombre


class VentanaBraille(wx.Frame):
    """Ventana externa con la transcripción braille del documento (B6)."""

    def __init__(self, padre: wx.Frame) -> None:
        super().__init__(padre, title=_("Transcripción braille (6 puntos)"))
        self._texto = wx.TextCtrl(self, style=wx.TE_MULTILINE | wx.TE_READONLY)
        self._texto.SetName(_("Braille"))
        self.SetSize((700, 200))

    def mostrar(self, contenido: str) -> None:
        self._texto.ChangeValue(contenido)


class VentanaEditor(wx.Frame):
    """Ventana del editor lineal accesible."""

    def __init__(self, editor: Editor, transcriptor: Transcriptor) -> None:
        super().__init__(None, title=_("DISVIMAT — Editor científico accesible"))
        self._editor = editor
        self._transcriptor = transcriptor
        self._braille: VentanaBraille | None = None
        panel = wx.Panel(self)
        self._texto = wx.TextCtrl(panel, style=wx.TE_MULTILINE | wx.TE_READONLY)
        self._texto.SetName(_("Documento"))
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(self._texto, 1, wx.EXPAND | wx.ALL, 4)
        panel.SetSizer(sizer)
        self.CreateStatusBar()
        self._crear_menu()
        self.Bind(wx.EVT_CHAR_HOOK, self._al_tecla)
        self._texto.Bind(wx.EVT_CHAR, self._al_caracter)
        self._texto.SetFocus()
        self.SetSize((900, 400))

    # --- entrada -------------------------------------------------------------

    def _al_tecla(self, evento: wx.KeyEvent) -> None:
        teclas = tecla_canonica(evento)
        if teclas is not None:
            resultado = self._editor.pulsar(teclas)
            if resultado is not None:
                self._aplicar(resultado)
                return
        evento.Skip()

    def _al_caracter(self, evento: wx.KeyEvent) -> None:
        codigo = evento.GetUnicodeKey()
        if codigo == wx.WXK_NONE:
            evento.Skip()
            return
        caracter = chr(codigo)
        resultado = self._editor.pulsar(caracter)
        if resultado is None and (caracter.isalnum() or caracter == " "):
            resultado = self._editor.escribir(caracter)
        if resultado is not None:
            self._aplicar(resultado)
        else:
            evento.Skip()

    def _aplicar(self, resultado: Resultado) -> None:
        self._texto.ChangeValue(resultado.texto)
        self._texto.SetInsertionPoint(resultado.posicion)
        self.SetStatusText(resultado.verbalizacion)
        if self._braille is not None and self._braille.IsShown():
            self._braille.mostrar(self._transcriptor.unicode(self._editor.documento.raiz))

    # --- menú ----------------------------------------------------------------

    def _crear_menu(self) -> None:
        archivo = wx.Menu()
        importar = archivo.Append(wx.ID_OPEN, _("&Importar XHTML…") + "\tCtrl+I")
        exportar = archivo.Append(wx.ID_SAVEAS, _("&Exportar como XHTML…") + "\tCtrl+E")
        exportar_bra = archivo.Append(wx.ID_ANY, _("Exportar como &BRA (braille 6 puntos)…"))
        archivo.AppendSeparator()
        salir = archivo.Append(wx.ID_EXIT, _("&Salir"))
        ver = wx.Menu()
        ventana_braille = ver.Append(wx.ID_ANY, _("&Ventana braille") + "\tCtrl+6")
        barra = wx.MenuBar()
        barra.Append(archivo, _("&Archivo"))
        barra.Append(ver, _("&Ver"))
        self.SetMenuBar(barra)
        self.Bind(wx.EVT_MENU, self._importar, importar)
        self.Bind(wx.EVT_MENU, self._exportar_xhtml, exportar)
        self.Bind(wx.EVT_MENU, self._exportar_bra, exportar_bra)
        self.Bind(wx.EVT_MENU, self._alternar_braille, ventana_braille)
        self.Bind(wx.EVT_MENU, lambda _evento: self.Close(), salir)

    def _importar(self, _evento: wx.CommandEvent) -> None:
        dialogo = wx.FileDialog(
            self,
            _("Importar XHTML"),
            wildcard=_("Documentos XHTML") + " (*.xhtml;*.html;*.xml)|*.xhtml;*.html;*.xml",
            style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST,
        )
        if dialogo.ShowModal() != wx.ID_OK:
            return
        ruta = dialogo.GetPath()
        try:
            with open(ruta, encoding="utf-8") as archivo:
                contenido = archivo.read()
            nodos = FiltroMathML(self._editor.catalogo).desde_xhtml(contenido)
        except (OSError, ErrorDeFiltro) as error:
            wx.MessageBox(str(error), _("No se pudo importar"), wx.ICON_ERROR)
            return
        self._aplicar(self._editor.cargar(nodos))

    def _exportar_xhtml(self, _evento: wx.CommandEvent) -> None:
        dialogo = wx.FileDialog(
            self,
            _("Exportar como XHTML"),
            wildcard=_("Documento XHTML") + " (*.xhtml)|*.xhtml",
            style=wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT,
        )
        if dialogo.ShowModal() != wx.ID_OK:
            return
        ruta = dialogo.GetPath()
        exportador = ExportadorXHTML(self._editor.catalogo)
        contenido = exportador.documento_xhtml(self._editor.documento.raiz)
        with open(ruta, "w", encoding="utf-8") as archivo:
            archivo.write(contenido)
        self.SetStatusText(_("Exportado: {ruta}").format(ruta=ruta))

    def _exportar_bra(self, _evento: wx.CommandEvent) -> None:
        dialogo = wx.FileDialog(
            self,
            _("Exportar como BRA"),
            wildcard=_("Braille de 6 puntos") + " (*.bra)|*.bra",
            style=wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT,
        )
        if dialogo.ShowModal() != wx.ID_OK:
            return
        ruta = dialogo.GetPath()
        contenido = self._transcriptor.ascii(self._editor.documento.raiz)
        with open(ruta, "w", encoding="ascii") as archivo:
            archivo.write(contenido + "\n")
        self.SetStatusText(_("Exportado: {ruta}").format(ruta=ruta))

    def _alternar_braille(self, _evento: wx.CommandEvent) -> None:
        if self._braille is None:
            self._braille = VentanaBraille(self)
        if self._braille.IsShown():
            self._braille.Hide()
            return
        self._braille.mostrar(self._transcriptor.unicode(self._editor.documento.raiz))
        self._braille.Show()
        self._texto.SetFocus()


def main() -> None:
    lengua = os.environ.get("DISVIMAT_LENGUA", "es")
    perfil = os.environ.get("DISVIMAT_PERFIL")
    instalar(lengua)
    app = wx.App()
    ventana = VentanaEditor(
        crear_editor(lengua=lengua, perfil=perfil),
        crear_transcriptor(lengua=lengua),
    )
    ventana.Show()
    app.MainLoop()


if __name__ == "__main__":
    main()
