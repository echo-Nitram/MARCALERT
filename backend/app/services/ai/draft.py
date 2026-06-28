"""
Feature premium: borrador de escrito de oposición.
Solo disponible en tier Estudio o con créditos.
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


def generate_opposition_draft(alerta: "Alerta", db: "Session") -> str:
    """
    Genera un borrador del escrito de oposición usando Claude.
    Tier premium — costo controlado por créditos.
    """
    if not settings.anthropic_api_key:
        return "Claude no configurado. Contacte al administrador."

    sol = alerta.solicitud
    marca = alerta.marca_vigilada
    boletin = sol.boletin

    clases_vigilada = ", ".join(str(c) for c in (marca.clases_niza or []))
    clases_solicitada = ", ".join(str(c) for c in (sol.clases_niza or []))

    prompt = f"""Eres un abogado especialista en propiedad industrial uruguaya. Redacta un borrador profesional de escrito de oposición a una solicitud de marca.

DATOS:
- Marca oponente: "{marca.denominacion}" — Clases: {clases_vigilada}
- Titular oponente: {marca.cliente_nombre or '[NOMBRE DEL TITULAR]'}
- Nueva solicitud: "{sol.denominacion}" (Exp. {sol.expediente})
- Solicitante: {sol.solicitante or '[SOLICITANTE]'}
- Fecha de presentación de solicitud: {sol.fecha_presentacion.isoformat() if sol.fecha_presentacion else 'N/D'}
- Boletín N°{boletin.numero if boletin else '?'}, fecha {boletin.fecha_publicacion.isoformat() if boletin else 'N/D'}
- Clases solicitadas: {clases_solicitada}
- Score de colisión: {alerta.score_total:.0f}/100
- Detalle fonético: {alerta.detalle_fonetico}

INSTRUCCIONES:
- Redactar en español formal uruguayo.
- Citar similitud fonética/visual y riesgo de confusión del consumidor.
- Mencionar identidad o afinidad de clases de Niza.
- Incluir referencia a la Ley 17.011 (Ley de Marcas de Uruguay).
- Estructura: encabezado, fundamentos de hecho, fundamentos de derecho, petitorio.
- Usar [BRACKETS] para datos a completar por el agente.
- IMPORTANTE: este es un borrador; el agente debe revisar antes de presentar."""

    try:
        import anthropic
        client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
        message = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=2000,
            messages=[{"role": "user", "content": prompt}],
        )
        return message.content[0].text.strip()
    except Exception as e:
        logger.error(f"Error generando borrador de oposición: {e}")
        return f"Error generando borrador: {e}"
