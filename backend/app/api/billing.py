"""
API de facturación: Stripe Checkout, Customer Portal y webhooks.
"""
from fastapi import APIRouter, Depends, HTTPException, Request, Header
from pydantic import BaseModel
from sqlalchemy.orm import Session
from typing import Optional

from app.database import get_db
from app.models.tenant import Tenant, SubscriptionTier
from app.models.user import User
from app.services.auth import get_current_user, get_current_active_tenant
from app.services.billing.stripe_service import (
    create_checkout_session,
    create_portal_session,
    handle_webhook,
)
from app.config import get_settings

router = APIRouter(prefix="/api/billing", tags=["billing"])
settings = get_settings()


class CheckoutRequest(BaseModel):
    tier: SubscriptionTier


class CheckoutResponse(BaseModel):
    checkout_url: str


class PortalResponse(BaseModel):
    portal_url: str


class TierInfo(BaseModel):
    tier: str
    subscription_active: bool
    trial_ends_at: Optional[str]
    draft_credits: int
    marca_limit: int


@router.get("/tier", response_model=TierInfo)
def get_tier_info(
    current_user: User = Depends(get_current_user),
    tenant: Tenant = Depends(get_current_active_tenant),
):
    """Devuelve el tier activo y los límites del tenant."""
    limits = {
        SubscriptionTier.starter: 10,
        SubscriptionTier.pro: 50,
        SubscriptionTier.estudio: 999999,
    }
    return TierInfo(
        tier=tenant.tier.value,
        subscription_active=tenant.subscription_active,
        trial_ends_at=tenant.trial_ends_at.isoformat() if tenant.trial_ends_at else None,
        draft_credits=tenant.draft_credits,
        marca_limit=limits[tenant.tier],
    )


@router.post("/checkout", response_model=CheckoutResponse)
def checkout(
    req: CheckoutRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Crea una sesión de Stripe Checkout para suscribirse a un tier."""
    if not settings.stripe_secret_key:
        raise HTTPException(status_code=503, detail="Stripe no configurado")

    tenant = db.query(Tenant).filter(Tenant.id == current_user.tenant_id).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant no encontrado")

    success_url = f"{settings.frontend_url}/billing/success?session_id={{CHECKOUT_SESSION_ID}}"
    cancel_url = f"{settings.frontend_url}/billing/cancel"

    try:
        url = create_checkout_session(tenant, req.tier, success_url, cancel_url)
    except (ValueError, RuntimeError) as e:
        raise HTTPException(status_code=400, detail=str(e))

    return CheckoutResponse(checkout_url=url)


@router.post("/portal", response_model=PortalResponse)
def portal(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Redirige al Customer Portal de Stripe para gestionar la suscripción."""
    if not settings.stripe_secret_key:
        raise HTTPException(status_code=503, detail="Stripe no configurado")

    tenant = db.query(Tenant).filter(Tenant.id == current_user.tenant_id).first()
    if not tenant or not tenant.stripe_customer_id:
        raise HTTPException(
            status_code=400,
            detail="No hay suscripción activa asociada a este tenant",
        )

    return_url = f"{settings.frontend_url}/settings/billing"
    try:
        url = create_portal_session(tenant, return_url)
    except (ValueError, RuntimeError) as e:
        raise HTTPException(status_code=400, detail=str(e))

    return PortalResponse(portal_url=url)


@router.post("/webhook", include_in_schema=False)
async def stripe_webhook(
    request: Request,
    stripe_signature: str = Header(None, alias="stripe-signature"),
    db: Session = Depends(get_db),
):
    """
    Endpoint de webhooks de Stripe (sin auth JWT — validado por firma HMAC).
    Configurar en Stripe Dashboard → Developers → Webhooks.
    """
    if not stripe_signature:
        raise HTTPException(status_code=400, detail="Falta cabecera stripe-signature")

    payload = await request.body()
    try:
        result = handle_webhook(payload, stripe_signature, db)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return result
