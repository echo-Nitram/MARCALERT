"""
API de boletines: consultar estado de procesamiento y disparar ingesta manual.
"""
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.boletin import Boletin
from app.models.user import User
from app.models.tenant import Tenant
from app.services.auth import get_current_user, get_current_active_tenant

router = APIRouter(prefix="/api/boletines", tags=["boletines"])


class BoletinOut(BaseModel):
    id: str
    numero: int
    fecha_publicacion: str
    paginas: Optional[int]
    total_solicitudes: Optional[int]
    procesado: bool
    error_msg: Optional[str]


@router.get("/", response_model=List[BoletinOut])
def list_boletines(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant: Tenant = Depends(get_current_active_tenant),
):
    boletines = db.query(Boletin).order_by(Boletin.numero.desc()).limit(50).all()
    return [_to_out(b) for b in boletines]


@router.post("/ingest", status_code=202)
def trigger_ingestion(
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant: Tenant = Depends(get_current_active_tenant),
):
    """Dispara manualmente la ingesta del siguiente boletín (para admin/debugging)."""
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Solo admins pueden disparar ingesta manual")
    background_tasks.add_task(_run_ingest)
    return {"detail": "Ingesta iniciada en background"}


def _run_ingest():
    import logging
    from datetime import date
    from app.database import SessionLocal
    from app.services.ingest.pipeline import run_ingestion
    from app.services.ingest.downloader import scrape_index_for_number
    from app.models.boletin import Boletin
    log = logging.getLogger(__name__)
    db = SessionLocal()
    try:
        ultimo = db.query(Boletin.numero).filter(Boletin.procesado.is_(True)).order_by(Boletin.numero.desc()).first()
        if ultimo:
            ultimo_n = ultimo[0]
        else:
            # Primera ejecución: descubrir el último boletín real desde el índice DNPI
            ultimo_n = scrape_index_for_number(date.today().year)
            if ultimo_n is None:
                log.error("No se pudo determinar el último boletín desde el índice DNPI")
                return
            log.info(f"Primer arranque: último boletín detectado = {ultimo_n}, se procesará ese.")
            ultimo_n -= 1  # run_ingestion intentará ultimo_n + 1
        run_ingestion(db, ultimo_n)
    except Exception as e:
        log.error(f"Error en ingesta manual: {e}")
    finally:
        db.close()


def _to_out(b: Boletin) -> BoletinOut:
    return BoletinOut(
        id=str(b.id),
        numero=b.numero,
        fecha_publicacion=b.fecha_publicacion.isoformat(),
        paginas=b.paginas,
        total_solicitudes=b.total_solicitudes,
        procesado=b.procesado,
        error_msg=b.error_msg,
    )
