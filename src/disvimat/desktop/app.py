"""Ventana principal del editor (módulo de presentación B4, escritorio).

La ventana es deliberadamente delgada: normaliza las pulsaciones al
formato canónico de las tablas, se las pasa al :class:`Editor` del
núcleo y refleja el resultado en un control de texto nativo (que NVDA
lee al mover el caret) y en la línea de estado (la verbalización, que
NVDA lee con NVDA+Fin). La salida directa por síntesis y línea braille
llega en la Fase 2 con el add-on de NVDA.
"""

import wx

from disvimat.core.editor import Editor, Resultado, crear_editor
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


class VentanaEditor(wx.Frame):
    """Ventana del editor lineal accesible."""

    def __init__(self, editor: Editor) -> None:
        super().__init__(None, title="DISVIMAT — Editor científico accesible")
        self._editor = editor
        panel = wx.Panel(self)
        self._texto = wx.TextCtrl(panel, style=wx.TE_MULTILINE | wx.TE_READONLY)
        self._texto.SetName("Documento")
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

    # --- menú ----------------------------------------------------------------

    def _crear_menu(self) -> None:
        archivo = wx.Menu()
        exportar = archivo.Append(wx.ID_SAVEAS, "&Exportar como XHTML…\tCtrl+E")
        archivo.AppendSeparator()
        salir = archivo.Append(wx.ID_EXIT, "&Salir")
        barra = wx.MenuBar()
        barra.Append(archivo, "&Archivo")
        self.SetMenuBar(barra)
        self.Bind(wx.EVT_MENU, self._exportar, exportar)
        self.Bind(wx.EVT_MENU, lambda _evento: self.Close(), salir)

    def _exportar(self, _evento: wx.CommandEvent) -> None:
        dialogo = wx.FileDialog(
            self,
            "Exportar como XHTML",
            wildcard="Documento XHTML (*.xhtml)|*.xhtml",
            style=wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT,
        )
        if dialogo.ShowModal() != wx.ID_OK:
            return
        ruta = dialogo.GetPath()
        exportador = ExportadorXHTML(self._editor.catalogo)
        contenido = exportador.documento_xhtml(self._editor.documento.raiz)
        with open(ruta, "w", encoding="utf-8") as archivo:
            archivo.write(contenido)
        self.SetStatusText(f"Exportado: {ruta}")


def main() -> None:
    app = wx.App()
    ventana = VentanaEditor(crear_editor())
    ventana.Show()
    app.MainLoop()


if __name__ == "__main__":
    main()
