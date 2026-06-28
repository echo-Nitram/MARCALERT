"""
CRUD de marcas vigiladas (cartera del agente).
"""
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.marca import MarcaVigilada, SensibilidadUmbral, TipoMarca
from app.models.tenant import Tenant, SubscriptionTier
from app.models.user import User
from app.services.auth import get_current_user, get_current_active_tenant

router = APIRouter(prefix="/api/marcas", tags=["marcas"])

_TIER_LIMITS = {
    SubscriptionTier.starter: 10,
    SubscriptionTier.pro: 50,
    SubscriptionTier.estudio: 999999,
}


class MarcaIn(BaseModel):
    denominacion: str
    tipo: TipoMarca = TipoMarca.denominativa
    clases_niza: List[int]
    sensibilidad: SensibilidadUmbral = SensibilidadUmbral.medio
    cliente_nombre: Optional[str] = None
    notas: Optional[str] = None


class MarcaOut(BaseModel):
    id: str
    denominacion: str
    tipo: str
    clases_niza: List[int]
    sensibilidad: str
    cliente_nombre: Optional[str]
    notas: Optional[str]
    activa: int

    class Config:
        from_attributes = True


@router.get("/", response_model=List[MarcaOut])
def list_marcas(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant: Tenant = Depends(get_current_active_tenant),
):
    marcas = db.query(MarcaVigilada).filter(MarcaVigilada.tenant_id == tenant.id).all()
    return [_to_out(m) for m in marcas]


@router.post("/", response_model=MarcaOut, status_code=201)
def create_marca(
    data: MarcaIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant: Tenant = Depends(get_current_active_tenant),
):
    limit = _TIER_LIMITS.get(tenant.tier, 10)
    count = db.query(MarcaVigilada).filter(
        MarcaVigilada.tenant_id == tenant.id, MarcaVigilada.activa == 1
    ).count()
    if count >= limit:
        raise HTTPException(
            status_code=403,
            detail=f"Límite de marcas alcanzado ({limit}) para su plan {tenant.tier.value}",
        )

    marca = MarcaVigilada(
        tenant_id=tenant.id,
        denominacion=data.denominacion,
        tipo=data.tipo,
        clases_niza=data.clases_niza,
        sensibilidad=data.sensibilidad,
        cliente_nombre=data.cliente_nombre,
        notas=data.notas,
    )
    db.add(marca)
    db.commit()
    db.refresh(marca)
    return _to_out(marca)


@router.put("/{marca_id}", response_model=MarcaOut)
def update_marca(
    marca_id: UUID,
    data: MarcaIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant: Tenant = Depends(get_current_active_tenant),
):
    marca = _get_or_404(db, marca_id, tenant.id)
    for field, val in data.model_dump(exclude_unset=True).items():
        setattr(marca, field, val)
    db.commit()
    db.refresh(marca)
    return _to_out(marca)


@router.delete("/{marca_id}", status_code=204)
def delete_marca(
    marca_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant: Tenant = Depends(get_current_active_tenant),
):
    marca = _get_or_404(db, marca_id, tenant.id)
    marca.activa = 0
    db.commit()


def _get_or_404(db: Session, marca_id: UUID, tenant_id) -> MarcaVigilada:
    m = db.query(MarcaVigilada).filter(
        MarcaVigilada.id == marca_id, MarcaVigilada.tenant_id == tenant_id
    ).first()
    if not m:
        raise HTTPException(status_code=404, detail="Marca no encontrada")
    return m


def _to_out(m: MarcaVigilada) -> MarcaOut:
    return MarcaOut(
        id=str(m.id),
        denominacion=m.denominacion,
        tipo=m.tipo.value,
        clases_niza=m.clases_niza or [],
        sensibilidad=m.sensibilidad.value,
        cliente_nombre=m.cliente_nombre,
        notas=m.notas,
        activa=m.activa,
    )
