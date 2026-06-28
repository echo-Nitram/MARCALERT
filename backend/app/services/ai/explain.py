"""
Capa B del embudo: Claude genera la explicación del riesgo en lenguaje natural.
Solo se invoca sobre alertas que ya superaron el filtro fonético/clase (capa A).

Costo controlado: se llama UNA VEZ por alerta, no por solicitud del boletín.
"""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.models.alerta import Alerta
    from sqlalchemy.orm import Session

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


def generate_collision_explanation(alerta: "Alerta", db: "Session") -> str:
    """
    Genera explicación del riesgo en lenguaje natural usando Claude.
    Devuelve string listo para reenviar al cliente final del agente.
    """
    if not settings.anthropic_api_key:
        return _fallback_explanation(alerta)

    try:
        import anthropic
        client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
    except ImportError:
        return _fallback_explanation(alerta)

    sol = alerta.solicitud
    marca = alerta.marca_vigilada
    detalle = alerta.detalle_fonetico or {}

    prompt = f"""Eres un experto en propiedad industrial uruguaya. Analiza la siguiente posible colisión de marcas y redacta una explicación concisa en español rioplatense formal, lista para enviar a un cliente:

MARCA VIGILADA: "{marca.denominacion}" — Clases Niza: {marca.clases_niza}
NUEVA SOLICITUD: "{sol.denominacion}" (Exp. {sol.expediente}) — Clases: {sol.clases_niza} — Solicitante: {sol.solicitante}

ANÁLISIS FONÉTICO:
- Score denominativo: {alerta.score_denominativo:.0f}/100
- Forma normalizada (marca vigilada): {detalle.get('norma1', '?')}
- Forma normalizada (solicitud): {detalle.get('norma2', '?')}
- Soundex coincide: {detalle.get('soundex_match', False)}
- Score de clase: {alerta.score_clase:.0f}/100
- Score total: {alerta.score_total:.0f}/100

Redacta 2-3 oraciones explicando: (1) por qué hay riesgo de confusión fonética, (2) la relación de clases Niza, (3) la recomendación (¿vale la pena oponerse?). Sé directo y profesional. No uses markdown ni bullets."""

    try:
        message = client.messages.create(
            model="claude-haiku-4-5-20251001",  # modelo más barato para explicaciones
            max_tokens=300,
            messages=[{"role": "user", "content": prompt}],
        )
        return message.content[0].text.strip()
    except Exception as e:
        logger.error(f"Error llamando a Claude para explicación: {e}")
        return _fallback_explanation(alerta)


def _fallback_explanation(alerta: "Alerta") -> str:
    """Explicación determinística si la IA no está disponible."""
    sol = alerta.solicitud
    marca = alerta.marca_vigilada
    clases_str = ", ".join(str(c) for c in (sol.clases_niza or []))
    return (
        f"La solicitud '{sol.denominacion}' (Exp. {sol.expediente}) presenta similitud "
        f"fonética con '{marca.denominacion}' con un score de {alerta.score_total:.0f}/100. "
        f"Clases solicitadas: {clases_str}. Se recomienda evaluar la presentación de oposición."
    )
