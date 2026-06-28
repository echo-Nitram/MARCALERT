"""
Motor fonético rioplatense para comparación denominativa de marcas.

Implementa las transformaciones características del español rioplatense:
- Seseo: c(e,i)/z → s
- Yeísmo: ll → y
- Betacismo: v → b

Pipeline:
1. Normalizar Unicode (eliminar acentos).
2. Aplicar transformaciones fonéticas rioplatenses.
3. Calcular Levenshtein ponderado entre formas normalizadas.
4. Calcular Soundex adaptado al español.
5. Combinar en score 0–100.

NO usa IA: es determinístico, rápido y preciso para fonética rioplatense.
"""
from __future__ import annotations

import re
import unicodedata
from typing import Optional

try:
    from rapidfuzz.distance import Levenshtein
    _USE_RAPIDFUZZ = True
except ImportError:
    _USE_RAPIDFUZZ = False


def normalize_rioplatense(text: str) -> str:
    """
    Convierte texto a su forma fonética rioplatense normalizada.
    Devuelve string en minúsculas sin acentos con transformaciones aplicadas.
    """
    s = text.upper().strip()

    # Eliminar caracteres no alfabéticos ni espacios (salvo apóstrofo)
    s = re.sub(r"[^A-ZÁÉÍÓÚÜÑ\s]", " ", s)

    # Eliminar acentos (NFD + filtrar combining marks)
    s = unicodedata.normalize("NFD", s)
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")

    # Llevar a minúsculas
    s = s.lower()

    # Seseo: ce/ci → se/si; z → s
    s = re.sub(r"c([ei])", r"s\1", s)
    s = s.replace("z", "s")

    # Yeísmo: ll → y
    s = s.replace("ll", "y")

    # Betacismo: v → b
    s = s.replace("v", "b")

    # qu → k (antes de e/i)
    s = re.sub(r"qu([ei])", r"k\1", s)

    # Aspiración de h (silenciosa en español)
    s = s.replace("h", "")

    # Reducir espacios
    s = re.sub(r"\s+", " ", s).strip()

    return s


def soundex_es(word: str) -> str:
    """
    Soundex adaptado al español rioplatense.
    Primero aplica normalización fonética, luego Soundex estándar con tabla española.
    """
    w = normalize_rioplatense(word).replace(" ", "")
    if not w:
        return "0000"

    # Tabla de códigos Soundex ajustada para español
    _SOUNDEX_MAP = {
        "b": "1", "p": "1", "f": "1",
        "c": "2", "g": "2", "j": "2", "k": "2", "q": "2", "s": "2", "x": "2", "s": "2",
        "d": "3", "t": "3",
        "l": "4",
        "m": "5", "n": "5",
        "r": "6",
    }

    first = w[0].upper()
    code = first
    prev = _SOUNDEX_MAP.get(w[0], "0")

    for char in w[1:]:
        c = _SOUNDEX_MAP.get(char, "0")
        if c != "0" and c != prev:
            code += c
        prev = c
        if len(code) == 4:
            break

    return code.ljust(4, "0")


def levenshtein_distance(a: str, b: str) -> int:
    """Distancia de edición (Levenshtein) entre dos strings."""
    if _USE_RAPIDFUZZ:
        return Levenshtein.distance(a, b)
    # Fallback puro Python
    if len(a) < len(b):
        a, b = b, a
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        curr = [i]
        for j, cb in enumerate(b, 1):
            cost = 0 if ca == cb else 1
            curr.append(min(prev[j] + 1, curr[j - 1] + 1, prev[j - 1] + cost))
        prev = curr
    return prev[-1]


def denominative_score(marca1: str, marca2: str) -> dict:
    """
    Calcula el score de similitud denominativa entre dos marcas.

    Returns dict con:
    - score: int 0–100
    - metodo: str
    - norma1, norma2: formas normalizadas
    - distancia: int (Levenshtein sobre formas normalizadas)
    - soundex_match: bool
    """
    n1 = normalize_rioplatense(marca1)
    n2 = normalize_rioplatense(marca2)

    if not n1 or not n2:
        return {"score": 0, "metodo": "vacio", "norma1": n1, "norma2": n2}

    # Coincidencia exacta tras normalización fonética
    if n1 == n2:
        return {
            "score": 100,
            "metodo": "exacto_fonetico",
            "norma1": n1,
            "norma2": n2,
            "distancia": 0,
            "soundex_match": True,
        }

    # Levenshtein sobre formas normalizadas
    max_len = max(len(n1), len(n2))
    dist = levenshtein_distance(n1, n2)
    lev_score = max(0, 100 - int(dist * 100 / max_len))

    # Soundex
    s1 = soundex_es(marca1)
    s2 = soundex_es(marca2)
    soundex_match = s1 == s2
    soundex_bonus = 10 if soundex_match else 0

    # Substring bonus: una contiene a la otra (ej. COSTA FINA / COSTAFINA)
    n1_clean = n1.replace(" ", "")
    n2_clean = n2.replace(" ", "")
    substring_bonus = 0
    if n1_clean in n2_clean or n2_clean in n1_clean:
        substring_bonus = 15

    score = min(100, lev_score + soundex_bonus + substring_bonus)

    return {
        "score": score,
        "metodo": "levenshtein+soundex",
        "norma1": n1,
        "norma2": n2,
        "distancia": dist,
        "soundex1": s1,
        "soundex2": s2,
        "soundex_match": soundex_match,
    }
