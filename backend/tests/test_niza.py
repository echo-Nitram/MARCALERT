"""
Tests del módulo de afinidad de clases de Niza.
"""
import pytest
from app.services.matching.niza import class_affinity_score, combine_scores


def test_misma_clase():
    assert class_affinity_score([30], [30]) == 100.0


def test_clases_distintas_sin_afinidad():
    assert class_affinity_score([1], [41]) == 0.0


def test_alimentos_restauracion():
    # Clase 30 (alimentos) y 43 (restauración) son afines
    score = class_affinity_score([30], [43])
    assert score >= 70


def test_software_hardware():
    score = class_affinity_score([9], [42])
    assert score >= 80


def test_multiples_clases():
    # Si comparten al menos una clase, score alto
    score = class_affinity_score([30, 35], [30, 43])
    assert score == 100.0


def test_combine_scores_sin_figurativo():
    score = combine_scores(80.0, 90.0)
    assert 80 < score <= 100


def test_combine_scores_con_figurativo():
    score = combine_scores(80.0, 90.0, score_figurativo=70.0)
    # El figurativo reduce ligeramente si es menor
    assert score < combine_scores(80.0, 90.0)
