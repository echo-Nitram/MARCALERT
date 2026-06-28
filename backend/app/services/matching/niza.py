"""
Afinidad entre clases de Niza.

No solo match exacto: clases relacionadas por actividad económica comparten
riesgo de confusión (ej. clase 30 y 43 en alimentos/restauración).

Tabla de afinidad basada en práctica IP: score 0–100.
- 100: misma clase
- 70–90: clases relacionadas (ej. producción + venta + servicio del mismo sector)
- 30–50: clases parcialmente relacionadas
- 0: sin relación
"""
from __future__ import annotations

# Grupos de clases relacionadas (afinidad alta ~80)
# Basado en práctica común IP; ajustar con feedback de agentes
_RELATED_GROUPS: list[frozenset[int]] = [
    # Alimentos y restauración
    frozenset({29, 30, 31, 43}),
    # Ropa y accesorios
    frozenset({18, 24, 25}),
    # Tecnología y telecomunicaciones
    frozenset({9, 38, 42}),
    # Salud y farmacia
    frozenset({3, 5, 44}),
    # Construcción y materiales
    frozenset({6, 17, 19, 37}),
    # Transporte y logística
    frozenset({12, 39}),
    # Educación y entretenimiento
    frozenset({16, 41}),
    # Servicios empresariales
    frozenset({35, 36}),
    # Química y pinturas
    frozenset({1, 2}),
    # Bebidas
    frozenset({32, 33}),
    # Animales
    frozenset({31, 44}),
    # Metales y maquinaria
    frozenset({6, 7, 8, 11}),
]

# Afinidad directa entre pares (score override)
_PAIR_AFFINITY: dict[frozenset[int], int] = {
    # alimentos industriales y ventas de alimentos
    frozenset({29, 30}): 85,
    frozenset({30, 43}): 80,
    frozenset({29, 43}): 75,
    # ropa + tiendas
    frozenset({25, 35}): 70,
    # software + hardware
    frozenset({9, 42}): 85,
    # telecomunicaciones + software
    frozenset({38, 42}): 80,
    # bebidas alcohólicas y no alcohólicas
    frozenset({32, 33}): 85,
    # educación + publicaciones
    frozenset({16, 41}): 75,
    # farmacia + servicios médicos
    frozenset({5, 44}): 80,
    # cosméticos + farmacia
    frozenset({3, 5}): 70,
}


def class_affinity_score(classes_a: list[int], classes_b: list[int]) -> float:
    """
    Devuelve el score de afinidad entre dos conjuntos de clases de Niza.
    Score 0–100 donde 100 = misma clase exacta.
    """
    if not classes_a or not classes_b:
        return 0.0

    best = 0.0
    for ca in classes_a:
        for cb in classes_b:
            score = _pair_score(ca, cb)
            if score > best:
                best = score

    return best


def _pair_score(ca: int, cb: int) -> float:
    if ca == cb:
        return 100.0

    pair = frozenset({ca, cb})

    # Override directo
    if pair in _PAIR_AFFINITY:
        return float(_PAIR_AFFINITY[pair])

    # Grupo compartido
    for group in _RELATED_GROUPS:
        if ca in group and cb in group:
            return 70.0

    return 0.0


def combine_scores(
    score_denominativo: float,
    score_clase: float,
    score_figurativo: float | None = None,
    peso_denom: float = 0.6,
    peso_clase: float = 0.4,
) -> float:
    """
    Combina scores de las capas A y C en un score total 0–100.
    La capa A (denominativo + clase) pesa por defecto 60/40.
    Si hay score figurativo (capa C), se promedia con pesos ajustados.
    """
    base = score_denominativo * peso_denom + score_clase * peso_clase
    if score_figurativo is not None:
        # Para marcas mixtas/figurativas: peso figurativo 30%
        base = base * 0.7 + score_figurativo * 0.3
    return round(min(100.0, base), 2)
