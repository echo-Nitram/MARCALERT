"""
API de alertas: dashboard y acciones del agente (marcar estado, pedir borrador).
"""
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.alerta import Alerta, EstadoAlerta
from app.models.tenant import Tenant, SubscriptionTier
from app.models.user import User
from app.services.auth import get_current_user, get_current_active_tenant

router = APIRouter(prefix="/api/alertas", tags=["alertas"])


class AlertaOut(BaseModel):
    id: str
    marca_vigilada_id: str
    solicitud_id: str
    score_total: float
    score_denominativo: float
    score_clase: float
    score_figurativo: Optional[float]
    explicacion_ia: Optional[str]
    fecha_limite_oposicion: Optional[str]
    dias_habiles_restantes: Optional[int]
    estado: str
    # Solicitud info (desnormalizado para el frontend)
    denominacion_solicitada: Optional[str] = None
    expediente: Optional[str] = None
    solicitante: Optional[str] = None
    clases_niza: Optional[List[int]] = None
    boletin_numero: Optional[int] = None
    # Marca vigilada
    denominacion_vigilada: Optional[str] = None

    class Config:
        from_attributes = True


class EstadoUpdate(BaseModel):
    estado: EstadoAlerta


@router.get("/", response_model=List[AlertaOut])
def list_alertas(
    estado: Optional[EstadoAlerta] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant: Tenant = Depends(get_current_active_tenant),
):
    q = db.query(Alerta).filter(Alerta.tenant_id == tenant.id)
    if estado:
        q = q.filter(Alerta.estado == estado)
    alertas = q.order_by(Alerta.created_at.desc()).all()
    return [_to_out(a) for a in alertas]


@router.patch("/{alerta_id}/estado", response_model=AlertaOut)
def update_estado(
    alerta_id: UUID,
    data: EstadoUpdate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant: Tenant = Depends(get_current_active_tenant),
):
    alerta = _get_or_404(db, alerta_id, tenant.id)
    alerta.estado = data.estado

    # Si pasa a "en_oposicion" y es tier estudio, generar borrador en background
    if data.estado == EstadoAlerta.en_oposicion and tenant.tier == SubscriptionTier.estudio:
        background_tasks.add_task(_generate_draft, str(alerta.id))

    db.commit()
    db.refresh(alerta)
    return _to_out(alerta)


@router.post("/{alerta_id}/borrador", response_model=AlertaOut)
def request_borrador(
    alerta_id: UUID,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant: Tenant = Depends(get_current_active_tenant),
):
    """Solicita la generación del borrador de oposición (feature premium)."""
    alerta = _get_or_404(db, alerta_id, tenant.id)

    if tenant.tier != SubscriptionTier.estudio and tenant.draft_credits <= 0:
        raise HTTPException(
            status_code=403,
            detail="Sin créditos de borrador. Actualice a plan Estudio o adquiera créditos.",
        )

    if tenant.tier != SubscriptionTier.estudio:
        tenant.draft_credits -= 1
        db.commit()

    background_tasks.add_task(_generate_draft, str(alerta.id))
    return _to_out(alerta)


def _generate_draft(alerta_id: str):
    """Genera el borrador de oposición usando Claude (capa B/C)."""
    from app.database import SessionLocal
    from app.services.ai.draft import generate_opposition_draft
    db = SessionLocal()
    try:
        alerta = db.query(Alerta).filter(Alerta.id == alerta_id).first()
        if not alerta:
            return
        draft = generate_opposition_draft(alerta, db)
        from datetime import datetime
        alerta.borrador_oposicion = draft
        alerta.borrador_generado_at = datetime.utcnow()
        db.commit()
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"Error generando borrador {alerta_id}: {e}")
    finally:
        db.close()


def _get_or_404(db: Session, alerta_id: UUID, tenant_id) -> Alerta:
    a = db.query(Alerta).filter(Alerta.id == alerta_id, Alerta.tenant_id == tenant_id).first()
    if not a:
        raise HTTPException(status_code=404, detail="Alerta no encontrada")
    return a


def _to_out(a: Alerta) -> AlertaOut:
    sol = a.solicitud
    marca = a.marca_vigilada
    return AlertaOut(
        id=str(a.id),
        marca_vigilada_id=str(a.marca_vigilada_id),
        solicitud_id=str(a.solicitud_id),
        score_total=a.score_total,
        score_denominativo=a.score_denominativo,
        score_clase=a.score_clase,
        score_figurativo=a.score_figurativo,
        explicacion_ia=a.explicacion_ia,
        fecha_limite_oposicion=(
            a.fecha_limite_oposicion.isoformat() if a.fecha_limite_oposicion else None
        ),
        dias_habiles_restantes=a.dias_habiles_restantes,
        estado=a.estado.value,
        denominacion_solicitada=sol.denominacion if sol else None,
        expediente=sol.expediente if sol else None,
        solicitante=sol.solicitante if sol else None,
        clases_niza=sol.clases_niza if sol else None,
        boletin_numero=sol.boletin_numero if sol else None,
        denominacion_vigilada=marca.denominacion if marca else None,
    )
