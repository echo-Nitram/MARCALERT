"""
Pipeline de ingesta completo: descarga → parseo → matching → alertas.

Orquesta las etapas 2–5 del spec.
"""
from __future__ import annotations

import logging
import os
import tempfile
from datetime import date
from typing import Optional

from sqlalchemy.orm import Session

from app.config import get_settings
from app.models.boletin import Boletin, Solicitud
from app.models.alerta import Alerta, EstadoAlerta, MetricaBoletin
from app.models.marca import MarcaVigilada
from app.services.ingest.downloader import download_boletin, check_boletin_exists, health_check_needed
from app.services.parser.pdf_parser import parse_boletin, SolicitudExtraida
from app.services.matching.phonetic import denominative_score
from app.services.matching.niza import class_affinity_score, combine_scores
from app.services.calendar.uruguay import compute_oposicion_deadline, business_days_between
from app.services.notifications.email import send_alert_email, send_admin_health_alert

logger = logging.getLogger(__name__)
settings = get_settings()


def run_ingestion(
    db: Session,
    ultimo_numero: int,
    pdf_storage_dir: str = "/tmp/marcalert_pdfs",
) -> Optional[int]:
    """
    Intenta ingestar el siguiente boletín (ultimo_numero + 1).
    Devuelve el número del boletín procesado, o None si no hay nuevo boletín.
    """
    os.makedirs(pdf_storage_dir, exist_ok=True)
    siguiente = ultimo_numero + 1

    # Verificar existencia
    existe, status = check_boletin_exists(siguiente)
    if not existe:
        if status not in (404, -1):
            # Código inesperado → health alert al admin
            send_admin_health_alert(
                f"URL del boletín {siguiente} devolvió status {status} (esperado 200 o 404). "
                "Posible cambio en la estructura del sitio DNPI."
            )
        logger.info(f"Boletín {siguiente} no disponible (status={status})")
        return None

    # Descargar
    pdf_path = download_boletin(siguiente, pdf_storage_dir)
    if not pdf_path:
        logger.error(f"No se pudo descargar el boletín {siguiente}")
        return None

    # Parsear
    logger.info(f"Parseando boletín {siguiente}...")
    try:
        boletin_data = parse_boletin(pdf_path)
    except Exception as e:
        logger.error(f"Error al parsear boletín {siguiente}: {e}")
        _register_boletin_error(db, siguiente, pdf_path, str(e))
        return None

    # Persistir boletín
    boletin_db = _persist_boletin(db, boletin_data, pdf_path)

    # Correr matching contra todas las marcas vigiladas de todos los tenants
    _run_matching_all_tenants(db, boletin_db, boletin_data)

    # Marcar como procesado
    from datetime import datetime
    boletin_db.procesado = True
    boletin_db.procesado_at = datetime.utcnow()
    boletin_db.total_solicitudes = len(boletin_data.solicitudes)
    db.commit()

    logger.info(
        f"Boletín {siguiente} procesado: "
        f"{len(boletin_data.solicitudes)} solicitudes analizadas"
    )
    return siguiente


def _register_boletin_error(db: Session, numero: int, pdf_path: str, error: str):
    from datetime import datetime
    from app.services.ingest.downloader import build_boletin_url
    boletin = Boletin(
        numero=numero,
        fecha_publicacion=date.today(),
        pdf_url=build_boletin_url(numero),
        procesado=False,
        error_msg=error,
    )
    db.add(boletin)
    db.commit()


def _persist_boletin(db: Session, boletin_data, pdf_path: str) -> Boletin:
    from app.services.ingest.downloader import build_boletin_url
    import os

    boletin_db = Boletin(
        numero=boletin_data.numero,
        fecha_publicacion=boletin_data.fecha_publicacion,
        pdf_url=build_boletin_url(boletin_data.numero),
        pdf_size_bytes=os.path.getsize(pdf_path),
        paginas=boletin_data.paginas,
        procesado=False,
    )
    db.add(boletin_db)
    db.flush()  # obtener el ID

    for sol in boletin_data.solicitudes:
        sol_db = _solicitud_to_model(sol, boletin_db)
        db.add(sol_db)

    db.commit()
    db.refresh(boletin_db)
    return boletin_db


def _solicitud_to_model(sol: SolicitudExtraida, boletin_db: Boletin) -> Solicitud:
    return Solicitud(
        boletin_id=boletin_db.id,
        boletin_numero=boletin_db.numero,
        expediente=sol.expediente,
        denominacion=sol.denominacion,
        solicitante=sol.solicitante,
        pais_solicitante=sol.pais_solicitante,
        fecha_presentacion=sol.fecha_presentacion,
        clases_niza=sol.clases_niza or [],
        agente_direccion=sol.agente_direccion,
        colores_reivindicados=sol.colores_reivindicados,
        pagina_boletin=sol.pagina,
        logo_data=sol.logo_data,
        logo_mime=sol.logo_mime,
        logo_width_pt=sol.logo_width_pt,
        logo_height_pt=sol.logo_height_pt,
        raw_block=sol.raw_block,
        parsed_by_ai=sol.parsed_by_ai,
    )


def _run_matching_all_tenants(db: Session, boletin_db: Boletin, boletin_data):
    """Ejecuta el embudo de matching para todas las marcas vigiladas de todos los tenants."""
    from app.models.tenant import Tenant, SubscriptionTier

    # Cargar todas las marcas activas
    marcas: list[MarcaVigilada] = db.query(MarcaVigilada).filter(MarcaVigilada.activa == 1).all()
    if not marcas:
        return

    # Cargar solicitudes del boletín
    solicitudes_db: list[Solicitud] = (
        db.query(Solicitud)
        .filter(Solicitud.boletin_id == boletin_db.id)
        .all()
    )

    # Por tenant: contar métricas
    metricas: dict = {}

    for marca in marcas:
        tenant_id = str(marca.tenant_id)
        if tenant_id not in metricas:
            metricas[tenant_id] = {"analizadas": 0, "colisiones": 0, "descartadas": 0}

        for sol in solicitudes_db:
            metricas[tenant_id]["analizadas"] += 1
            alerta = _check_collision(marca, sol, boletin_db.fecha_publicacion)
            if alerta:
                db.add(alerta)
                metricas[tenant_id]["colisiones"] += 1
            else:
                metricas[tenant_id]["descartadas"] += 1

    db.flush()

    # Guardar métricas y enviar notificaciones
    for tenant_id, m in metricas.items():
        metrica = MetricaBoletin(
            tenant_id=tenant_id,
            boletin_numero=boletin_db.numero,
            total_solicitudes_analizadas=m["analizadas"],
            total_colisiones_detectadas=m["colisiones"],
            total_descartadas=m["descartadas"],
        )
        db.add(metrica)

    db.commit()

    # Notificar alertas nuevas por email
    _notify_new_alerts(db, boletin_db)


def _check_collision(
    marca: MarcaVigilada,
    sol: Solicitud,
    fecha_publicacion: date,
) -> Optional[Alerta]:
    """
    Capa A: matching fonético + afinidad de clases.
    Si el score supera el umbral del tenant, crea la alerta.
    """
    if not sol.denominacion or not marca.denominacion:
        return None

    # Score denominativo (capa A)
    denom_result = denominative_score(marca.denominacion, sol.denominacion)
    score_denom = denom_result["score"]

    # Score de clase (capa A)
    score_clase = class_affinity_score(marca.clases_niza or [], sol.clases_niza or [])

    # Score total
    score_total = combine_scores(score_denom, score_clase)

    if score_total < marca.score_threshold:
        return None

    # Calcular deadline de oposición
    from app.config import get_settings
    settings = get_settings()
    fecha_limite = compute_oposicion_deadline(
        fecha_publicacion, settings.oposicion_dias_habiles
    )
    dias_restantes = business_days_between(date.today(), fecha_limite)

    return Alerta(
        tenant_id=marca.tenant_id,
        marca_vigilada_id=marca.id,
        solicitud_id=sol.id,
        score_denominativo=score_denom,
        score_clase=score_clase,
        score_total=score_total,
        detalle_fonetico=denom_result,
        fecha_limite_oposicion=fecha_limite,
        dias_habiles_restantes=dias_restantes,
        estado=EstadoAlerta.nueva,
    )


def _notify_new_alerts(db: Session, boletin_db: Boletin):
    """Envía email por cada alerta nueva (agrupado por tenant)."""
    from app.models.user import User
    from app.models.tenant import Tenant
    import collections

    alertas_nuevas: list[Alerta] = (
        db.query(Alerta)
        .join(Solicitud)
        .filter(
            Solicitud.boletin_id == boletin_db.id,
            Alerta.estado == EstadoAlerta.nueva,
            Alerta.notificado_email.is_(False),
        )
        .all()
    )

    if not alertas_nuevas:
        return

    # Agrupar por tenant
    by_tenant: dict = collections.defaultdict(list)
    for alerta in alertas_nuevas:
        by_tenant[str(alerta.tenant_id)].append(alerta)

    for tenant_id, tenant_alertas in by_tenant.items():
        # Obtener usuarios con notificación por email activa
        users = (
            db.query(User)
            .filter(User.tenant_id == tenant_id, User.notify_email.is_(True), User.is_active.is_(True))
            .all()
        )
        for user in users:
            try:
                send_alert_email(user.email, tenant_alertas, boletin_db, db)
                for a in tenant_alertas:
                    a.notificado_email = True
            except Exception as e:
                logger.error(f"Error enviando email a {user.email}: {e}")

    db.commit()
