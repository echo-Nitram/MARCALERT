"""
Notificaciones por email usando Resend.
Canal primario para alertas de colisión.
"""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from sqlalchemy.orm import Session
    from app.models.alerta import Alerta
    from app.models.boletin import Boletin

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


def send_alert_email(
    to_email: str,
    alertas: list["Alerta"],
    boletin: "Boletin",
    db: "Session",
) -> None:
    """Envía email con las alertas de colisión detectadas en un boletín."""
    if not settings.resend_api_key:
        logger.warning("RESEND_API_KEY no configurada; email no enviado")
        return

    try:
        import resend
        resend.api_key = settings.resend_api_key
    except ImportError:
        logger.warning("Paquete resend no disponible")
        return

    subject = (
        f"[MARCALERT] {len(alertas)} colisión(es) detectada(s) — "
        f"Boletín N°{boletin.numero} ({boletin.fecha_publicacion.strftime('%d/%m/%Y')})"
    )
    html = _build_alert_html(alertas, boletin, db)

    resend.Emails.send({
        "from": settings.email_from,
        "to": [to_email],
        "subject": subject,
        "html": html,
    })
    logger.info(f"Email enviado a {to_email}: {len(alertas)} alerta(s)")


def send_admin_health_alert(message: str) -> None:
    """Envía alerta de health check al admin (no al cliente)."""
    if not settings.resend_api_key:
        logger.error(f"[HEALTH ALERT] {message}")
        return

    try:
        import resend
        resend.api_key = settings.resend_api_key
        resend.Emails.send({
            "from": settings.email_from,
            "to": [settings.admin_email],
            "subject": "[MARCALERT ADMIN] Health check fallido",
            "html": f"<p>{message}</p>",
        })
    except Exception as e:
        logger.error(f"Error enviando health alert: {e}. Mensaje original: {message}")


def _build_alert_html(alertas: list["Alerta"], boletin: "Boletin", db: "Session") -> str:
    """Construye el HTML del email de alertas."""
    rows = []
    for alerta in alertas:
        sol = alerta.solicitud
        marca = alerta.marca_vigilada
        deadline_str = (
            alerta.fecha_limite_oposicion.strftime("%d/%m/%Y")
            if alerta.fecha_limite_oposicion
            else "N/D"
        )
        clases = ", ".join(str(c) for c in (sol.clases_niza or []))
        rows.append(f"""
        <tr>
          <td style="padding:8px;border:1px solid #ddd">{sol.denominacion or "—"}</td>
          <td style="padding:8px;border:1px solid #ddd">{marca.denominacion}</td>
          <td style="padding:8px;border:1px solid #ddd">{sol.expediente}</td>
          <td style="padding:8px;border:1px solid #ddd">{clases}</td>
          <td style="padding:8px;border:1px solid #ddd;font-weight:bold">{alerta.score_total:.0f}/100</td>
          <td style="padding:8px;border:1px solid #ddd;color:#c00">
            {deadline_str}<br><small>(estimada — verificar DNPI)</small>
          </td>
        </tr>""")

    rows_html = "".join(rows)
    return f"""
    <html><body style="font-family:Arial,sans-serif;color:#333">
    <h2 style="color:#1a1a8c">MARCALERT — Alerta de colisión</h2>
    <p>Boletín N°{boletin.numero} del {boletin.fecha_publicacion.strftime('%d/%m/%Y')}</p>
    <p>Se detectaron <strong>{len(alertas)}</strong> posible(s) colisión(es) con su cartera:</p>

    <table style="border-collapse:collapse;width:100%">
      <thead>
        <tr style="background:#1a1a8c;color:white">
          <th style="padding:8px">Denominación solicitada</th>
          <th style="padding:8px">Su marca</th>
          <th style="padding:8px">Expediente</th>
          <th style="padding:8px">Clases Niza</th>
          <th style="padding:8px">Score</th>
          <th style="padding:8px">Límite oposición*</th>
        </tr>
      </thead>
      <tbody>{rows_html}</tbody>
    </table>

    <p style="margin-top:24px;font-size:12px;color:#666">
      * Fecha estimada calculada como {settings.oposicion_dias_habiles} días hábiles
      desde la publicación. <strong>Verificar siempre con DNPI y Ley 17.011.</strong>
    </p>
    <p style="font-size:12px;color:#666">
      MARCALERT — Sistema de vigilancia de marcas para Uruguay
    </p>
    </body></html>
    """
