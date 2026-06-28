"""
Tests del motor fonético rioplatense.
Casos reales de la práctica IP uruguaya.
"""
import pytest
from app.services.matching.phonetic import normalize_rioplatense, soundex_es, denominative_score


def test_seseo_basico():
    assert normalize_rioplatense("CERVEZA") == normalize_rioplatense("SERBESA")


def test_yeismo():
    n1 = normalize_rioplatense("LLAVE")
    n2 = normalize_rioplatense("YAVE")
    assert n1 == n2


def test_betacismo():
    n1 = normalize_rioplatense("BACA")
    n2 = normalize_rioplatense("VACA")
    assert n1 == n2


def test_h_silenciosa():
    n1 = normalize_rioplatense("HOLA")
    n2 = normalize_rioplatense("OLA")
    assert n1 == n2


def test_costa_fina_costafina():
    """Caso típico: espacios vs. concatenado."""
    result = denominative_score("COSTA FINA", "COSTAFINA")
    assert result["score"] >= 80, f"Score demasiado bajo: {result}"


def test_kostafina_costa_fina():
    """Seseo: K/C intercambiable fonéticamente."""
    result = denominative_score("COSTA FINA", "KOSTAFINA")
    assert result["score"] >= 75, f"Score demasiado bajo: {result}"


def test_marcas_distintas():
    result = denominative_score("MICROSOFT", "PEPSI")
    assert result["score"] < 30, f"Score demasiado alto para marcas distintas: {result}"


def test_exacto_fonetico():
    result = denominative_score("CERVEZA", "SERBESA")
    assert result["score"] == 100
    assert result["metodo"] == "exacto_fonetico"


def test_soundex_similar():
    s1 = soundex_es("GARCIA")
    s2 = soundex_es("GARSIA")
    assert s1 == s2


def test_score_identico():
    result = denominative_score("MARCALERT", "MARCALERT")
    assert result["score"] == 100


def test_normalize_acentos():
    n1 = normalize_rioplatense("CAFÉ")
    n2 = normalize_rioplatense("CAFE")
    assert n1 == n2
