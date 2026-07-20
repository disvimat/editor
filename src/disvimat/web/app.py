"""Aplicación web FastAPI del editor DISVIMAT.

Mantiene una sesión de edición por usuario (un :class:`Editor` del
núcleo en memoria) y expone la misma operativa que la versión de
escritorio: pulsar teclas, escribir caracteres, importar y exportar.
La presentación visual es MathML nativo, que los navegadores modernos
verbalizan; además, cada respuesta incluye la verbalización del núcleo
para anunciarla en una región ``aria-live``.
"""

import uuid
import xml.etree.ElementTree as ET
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, HTMLResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from disvimat.core.editor import Editor, Resultado, crear_editor
from disvimat.core.filtros.mathml import ErrorDeFiltro, FiltroMathML
from disvimat.core.transcripcion.braille import Transcriptor, crear_transcriptor
from disvimat.export.xhtml import ExportadorXHTML

_ESTATICOS = Path(__file__).resolve().parent / "static"


class Vista(BaseModel):
    """Lo que la página necesita para reflejar el estado del editor."""

    sesion: str
    texto: str
    posicion: int
    verbalizacion: str
    mathml: str


class PeticionTecla(BaseModel):
    """Una tecla de la página: combinación canónica y/o carácter imprimible."""

    teclas: str | None = None
    caracter: str | None = None


class PeticionImportar(BaseModel):
    xhtml: str


class _Sesion:
    """Editor y utilidades de exportación de una sesión de usuario."""

    def __init__(self, lengua: str, perfil: str | None) -> None:
        self.editor: Editor = crear_editor(lengua=lengua, perfil=perfil)
        self.transcriptor: Transcriptor = crear_transcriptor(lengua=lengua)
        self.exportador = ExportadorXHTML(self.editor.catalogo)

    def mathml(self) -> str:
        elemento = self.exportador.mathml(self.editor.documento.raiz)
        return ET.tostring(elemento, encoding="unicode")


def crear_app() -> FastAPI:
    """Construye la aplicación; las sesiones viven mientras corre el proceso."""
    app = FastAPI(title="DISVIMAT web")
    sesiones: dict[str, _Sesion] = {}

    def obtener(sesion_id: str) -> _Sesion:
        sesion = sesiones.get(sesion_id)
        if sesion is None:
            raise HTTPException(status_code=404, detail="sesión desconocida")
        return sesion

    def vista(sesion_id: str, sesion: _Sesion, resultado: Resultado) -> Vista:
        return Vista(
            sesion=sesion_id,
            texto=resultado.texto,
            posicion=resultado.posicion,
            verbalizacion=resultado.verbalizacion,
            mathml=sesion.mathml(),
        )

    @app.get("/", response_class=HTMLResponse)
    def indice() -> str:
        return (_ESTATICOS / "index.html").read_text(encoding="utf-8")

    @app.post("/api/sesion", response_model=Vista)
    def nueva_sesion(lengua: str = "es", perfil: str | None = None) -> Vista:
        sesion_id = uuid.uuid4().hex
        sesion = _Sesion(lengua=lengua, perfil=perfil)
        sesiones[sesion_id] = sesion
        return vista(sesion_id, sesion, sesion.editor.estado())

    @app.post("/api/sesion/{sesion_id}/tecla", response_model=Vista)
    def tecla(sesion_id: str, peticion: PeticionTecla) -> Vista:
        sesion = obtener(sesion_id)
        resultado: Resultado | None = None
        if peticion.teclas:
            resultado = sesion.editor.pulsar(peticion.teclas)
        if resultado is None and peticion.caracter:
            resultado = sesion.editor.escribir(peticion.caracter)
        if resultado is None:
            resultado = sesion.editor.estado()
        return vista(sesion_id, sesion, resultado)

    @app.post("/api/sesion/{sesion_id}/importar", response_model=Vista)
    def importar(sesion_id: str, peticion: PeticionImportar) -> Vista:
        sesion = obtener(sesion_id)
        try:
            nodos = FiltroMathML(sesion.editor.catalogo).desde_xhtml(peticion.xhtml)
        except ErrorDeFiltro as error:
            raise HTTPException(status_code=400, detail=str(error)) from error
        return vista(sesion_id, sesion, sesion.editor.cargar(nodos))

    def _descarga(contenido: str, nombre: str, tipo: str) -> PlainTextResponse:
        return PlainTextResponse(
            contenido,
            media_type=tipo,
            headers={"Content-Disposition": f'attachment; filename="{nombre}"'},
        )

    @app.get("/api/sesion/{sesion_id}/exportar.xhtml")
    def exportar_xhtml(sesion_id: str) -> PlainTextResponse:
        sesion = obtener(sesion_id)
        contenido = sesion.exportador.documento_xhtml(sesion.editor.documento.raiz)
        return _descarga(contenido, "documento.xhtml", "application/xhtml+xml")

    @app.get("/api/sesion/{sesion_id}/exportar.bra")
    def exportar_bra(sesion_id: str) -> PlainTextResponse:
        sesion = obtener(sesion_id)
        contenido = sesion.transcriptor.ascii(sesion.editor.documento.raiz) + "\n"
        return _descarga(contenido, "documento.bra", "text/plain")

    @app.get("/favicon.ico")
    def favicon() -> FileResponse:
        return FileResponse(_ESTATICOS / "favicon.svg", media_type="image/svg+xml")

    app.mount("/static", StaticFiles(directory=_ESTATICOS), name="static")
    return app


app = crear_app()


def main() -> None:
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8000)


if __name__ == "__main__":
    main()
