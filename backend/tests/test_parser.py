"""
Tests del parser INID.
Usa el caso de prueba real del spec: expediente 586527 del boletín 359.
Los tests de integración requieren el PDF real; los unitarios usan texto sintético.
"""
import pytest
from datetime import date
from app.services.parser.pdf_parser import (
    _parse_block,
    _parse_date,
    _parse_clases,
    _clean,
    _RE_PORTADA,
)


SAMPLE_BLOCK_359 = """(210) 586527
(540) ALGODON Y MAS
(730) juan martin aguiar gammenthaler; UY
(220) 20/05/2026
(511) 35 (S/D) y 43 (S/D)
(740) Baltasar Brum 828, Canelones, UY
(591) BLANCO Y NEGRO
"""


def test_parse_block_expediente():
    sol = _parse_block(SAMPLE_BLOCK_359, page_num=5)
    assert sol is not None
    assert sol.expediente == "586527"


def test_parse_block_denominacion():
    sol = _parse_block(SAMPLE_BLOCK_359, page_num=5)
    assert sol.denominacion == "ALGODON Y MAS"


def test_parse_block_solicitante():
    sol = _parse_block(SAMPLE_BLOCK_359, page_num=5)
    assert "aguiar" in sol.solicitante.lower()
    assert sol.pais_solicitante == "UY"


def test_parse_block_fecha():
    sol = _parse_block(SAMPLE_BLOCK_359, page_num=5)
    assert sol.fecha_presentacion == date(2026, 5, 20)


def test_parse_block_clases():
    sol = _parse_block(SAMPLE_BLOCK_359, page_num=5)
    assert 35 in sol.clases_niza
    assert 43 in sol.clases_niza


def test_parse_block_colores():
    sol = _parse_block(SAMPLE_BLOCK_359, page_num=5)
    assert "BLANCO" in (sol.colores_reivindicados or "")


def test_portada_regex():
    texto = "Boletín de la Propiedad Industrial N°359 15/06/2026"
    m = _RE_PORTADA.search(texto)
    assert m is not None
    assert m.group(1) == "359"
    assert m.group(4) == "2026"


def test_portada_regex_alternativo():
    texto = "Nº 359, 15/06/2026"
    m = _RE_PORTADA.search(texto)
    assert m is not None
    assert m.group(1) == "359"


def test_parse_date():
    assert _parse_date("20/05/2026") == date(2026, 5, 20)
    assert _parse_date("1/1/2025") == date(2025, 1, 1)
    assert _parse_date("texto inválido") is None


def test_parse_clases():
    clases = _parse_clases("35 (S/D) y 43 (S/D)")
    assert 35 in clases
    assert 43 in clases


def test_parse_clases_simple():
    assert _parse_clases("25") == [25]


def test_clean_whitespace():
    assert _clean("  hola   mundo  ") == "hola mundo"


def test_block_sin_210():
    sol = _parse_block("no tiene el marcador", page_num=0)
    assert sol is None
