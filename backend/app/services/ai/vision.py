"""
Capa C del embudo: Claude Vision compara logos de marcas figurativas.
Solo se invoca sobre el puñado de finalistas que ya superaron capa A.
NUNCA sobre el boletín entero (costo).
"""
from __future__ import annotations

import base64
import logging
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from app.models.alerta import Alerta

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


def compare_logos(
    logo_vigilada: bytes,
    logo_solicitada: bytes,
    mime: str = "image/png",
) -> dict:
    """
    Compara dos logos usando Claude Vision.
    Devuelve dict con score (0-100), razonamiento y clasificación Viena sugerida.
    """
    if not settings.anthropic_api_key:
        return {"score": 0, "razonamiento": "Claude no configurado", "viena": None}

    try:
        import anthropic
        client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
    except ImportError:
        return {"score": 0, "razonamiento": "anthropic no instalado", "viena": None}

    b64_a = base64.standard_b64encode(logo_vigilada).decode()
    b64_b = base64.standard_b64encode(logo_solicitada).decode()

    prompt = """Eres un experto en propiedad industrial. Compara estos dos logos de marcas y evalúa el riesgo de confusión visual.

Analiza:
1. Similitud visual general (colores, forma, composición)
2. Elementos conceptuales compartidos (¿ambos evocan lo mismo?)
3. Clasificación de Viena de cada logo (si puedes determinarla)

Responde con:
SCORE: [0-100 donde 100 = idénticos]
RAZONAMIENTO: [2-3 oraciones en español]
VIENA_A: [clasificación Viena del primer logo, si aplica]
VIENA_B: [clasificación Viena del segundo logo, si aplica]"""

    try:
        message = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=400,
            messages=[{
                "role": "user",
                "content": [
                    {"type": "text", "text": "Logo 1 (marca vigilada):"},
                    {"type": "image", "source": {"type": "base64", "media_type": mime, "data": b64_a}},
                    {"type": "text", "text": "Logo 2 (nueva solicitud):"},
                    {"type": "image", "source": {"type": "base64", "media_type": mime, "data": b64_b}},
                    {"type": "text", "text": prompt},
                ],
            }],
        )
        return _parse_vision_response(message.content[0].text)
    except Exception as e:
        logger.error(f"Error en Claude Vision: {e}")
        return {"score": 0, "razonamiento": str(e), "viena": None}


def _parse_vision_response(text: str) -> dict:
    import re
    score_m = re.search(r"SCORE:\s*(\d+)", text)
    reason_m = re.search(r"RAZONAMIENTO:\s*(.+?)(?=VIENA_A:|$)", text, re.DOTALL)
    viena_a_m = re.search(r"VIENA_A:\s*(.+?)(?=VIENA_B:|$)", text, re.DOTALL)
    viena_b_m = re.search(r"VIENA_B:\s*(.+)", text, re.DOTALL)

    return {
        "score": int(score_m.group(1)) if score_m else 0,
        "razonamiento": reason_m.group(1).strip() if reason_m else text,
        "viena_a": viena_a_m.group(1).strip() if viena_a_m else None,
        "viena_b": viena_b_m.group(1).strip() if viena_b_m else None,
    }
