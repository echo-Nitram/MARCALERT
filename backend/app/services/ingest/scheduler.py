"""
Scheduler con calendario hábil UY.

Usa APScheduler con cron para disparar:
1. Check de nuevo boletín cada día hábil (alrededor del 15 y fin de mes).
2. Health check si se esperaba un boletín y no llegó.
"""
from __future__ import annotations

import logging
from datetime import date, datetime

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.services.calendar.uruguay import is_business_day, next_expected_boletin_date
from app.services.ingest.downloader import health_check_needed
from app.services.notifications.email import send_admin_health_alert

logger = logging.getLogger(__name__)


def _get_last_processed_numero(db: Session) -> int:
    """Devuelve el número del último boletín procesado en la DB."""
    from app.models.boletin import Boletin
    result = db.query(Boletin.numero).filter(Boletin.procesado.is_(True)).order_by(Boletin.numero.desc()).first()
    # Si no hay ninguno, empezar desde 348 (2026 empieza en 349 según spec)
    return result[0] if result else 348


def check_new_boletin():
    """Tarea periódica: intenta ingestar el siguiente boletín."""
    hoy = date.today()
    if not is_business_day(hoy):
        return

    db = SessionLocal()
    try:
        from app.services.ingest.pipeline import run_ingestion
        ultimo = _get_last_processed_numero(db)
        result = run_ingestion(db, ultimo)
        if result:
            logger.info(f"Scheduler: boletín {result} procesado exitosamente")
        else:
            # Verificar si debería haber salido un boletín
            siguiente_esperado = next_expected_boletin_date(date.today() - __import__('datetime').timedelta(days=30))
            if health_check_needed(ultimo, siguiente_esperado, margen_dias=2):
                msg = (
                    f"HEALTH CHECK: Se esperaba el boletín {ultimo + 1} "
                    f"para {siguiente_esperado.isoformat()} y no está disponible. "
                    "Verificar manualmente en DNPI."
                )
                logger.warning(msg)
                send_admin_health_alert(msg)
    except Exception as e:
        logger.error(f"Error en scheduler check_new_boletin: {e}")
    finally:
        db.close()


def create_scheduler() -> BackgroundScheduler:
    """Crea y configura el scheduler de APScheduler."""
    scheduler = BackgroundScheduler(timezone="America/Montevideo")

    # Correr lunes a viernes cada 4 horas entre 8am y 6pm
    # Los boletines se publican a lo largo del día hábil
    scheduler.add_job(
        check_new_boletin,
        trigger=CronTrigger(
            day_of_week="mon-fri",
            hour="8,12,16",
            minute=0,
            timezone="America/Montevideo",
        ),
        id="check_new_boletin",
        replace_existing=True,
        misfire_grace_time=3600,
    )

    return scheduler
