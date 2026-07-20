"""API web: la misma operativa del núcleo servida por HTTP (adaptador web)."""

import pytest
from fastapi.testclient import TestClient

from disvimat.web.app import crear_app


@pytest.fixture
def cliente() -> TestClient:
    return TestClient(crear_app())


def nueva_sesion(cliente: TestClient) -> str:
    respuesta = cliente.post("/api/sesion")
    assert respuesta.status_code == 200
    datos = respuesta.json()
    assert datos["texto"] == ""
    return str(datos["sesion"])


def enviar(cliente: TestClient, sesion: str, teclas: str, caracter: str | None = None) -> dict:
    respuesta = cliente.post(
        f"/api/sesion/{sesion}/tecla", json={"teclas": teclas, "caracter": caracter}
    )
    assert respuesta.status_code == 200
    return dict(respuesta.json())


def test_pagina_principal_es_html_accesible(cliente: TestClient) -> None:
    cuerpo = cliente.get("/").text
    assert '<html lang="es">' in cuerpo
    assert 'role="application"' in cuerpo
    assert "aria-live" in cuerpo


def test_editar_fraccion_produce_texto_y_mathml(cliente: TestClient) -> None:
    sesion = nueva_sesion(cliente)
    for tecla in ["1", "+", "Ctrl+F"]:
        vista = enviar(cliente, sesion, tecla, tecla if len(tecla) == 1 else None)
    enviar(cliente, sesion, "2", "2")
    enviar(cliente, sesion, "Tab")
    vista = enviar(cliente, sesion, "3", "3")
    assert vista["texto"] == "1+(2∕3)"
    assert "<mfrac" in vista["mathml"]
    assert vista["verbalizacion"] == "3"


def test_caracter_imprimible_se_intenta_primero_como_signo(cliente: TestClient) -> None:
    sesion = nueva_sesion(cliente)
    vista = enviar(cliente, sesion, "+", "+")  # "+" es un signo, no texto literal
    assert vista["texto"] == "+"
    assert vista["verbalizacion"] == "más"


def test_calcular_por_la_api(cliente: TestClient) -> None:
    sesion = nueva_sesion(cliente)
    for tecla in ["2", "+", "3"]:
        enviar(cliente, sesion, tecla, tecla if len(tecla) == 1 else None)
    vista = enviar(cliente, sesion, "Ctrl+Return")
    assert vista["verbalizacion"] == "resultado: 5"


def test_importar_y_exportar(cliente: TestClient) -> None:
    sesion = nueva_sesion(cliente)
    for tecla in ["1", "+", "2"]:
        enviar(cliente, sesion, tecla, tecla if len(tecla) == 1 else None)
    xhtml = cliente.get(f"/api/sesion/{sesion}/exportar.xhtml")
    assert xhtml.status_code == 200
    assert "attachment" in xhtml.headers["content-disposition"]
    assert "<math" in xhtml.text

    otra = nueva_sesion(cliente)
    vista = cliente.post(f"/api/sesion/{otra}/importar", json={"xhtml": xhtml.text}).json()
    assert vista["texto"] == "1+2"


def test_exportar_bra(cliente: TestClient) -> None:
    sesion = nueva_sesion(cliente)
    enviar(cliente, sesion, "1", "1")
    bra = cliente.get(f"/api/sesion/{sesion}/exportar.bra")
    assert bra.status_code == 200
    assert bra.text.strip() == "#a"


def test_sesion_desconocida_da_404(cliente: TestClient) -> None:
    respuesta = cliente.post("/api/sesion/inexistente/tecla", json={"teclas": "1", "caracter": "1"})
    assert respuesta.status_code == 404


def test_importar_invalido_da_400(cliente: TestClient) -> None:
    sesion = nueva_sesion(cliente)
    respuesta = cliente.post(f"/api/sesion/{sesion}/importar", json={"xhtml": "<p>sin math</p>"})
    assert respuesta.status_code == 400
