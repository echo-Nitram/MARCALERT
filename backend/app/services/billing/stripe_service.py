"""
Integración con Stripe para suscripciones por tier.

Tiers (precios hipótesis — validar con entrevistas a agentes):
  Starter  → hasta 10 marcas — USD 29/mes
  Pro      → hasta 50 marcas — USD 79/mes
  Estudio  → ilimitadas + borradores — USD 199/mes

Trial: 30 días gratis al registrar el tenant.

Flujo:
  1. create_checkout_session → redirige a Stripe Hosted Checkout.
  2. Stripe dispara webhooks → handle_webhook() sincroniza el tier en DB.
  3. create_portal_session → permite al cliente gestionar su suscripción.
"""
from __future__ import annotations

import logging
from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Session

from app.config import get_settings
from app.models.tenant import Tenant, SubscriptionTier

logger = logging.getLogger(__name__)
settings = get_settings()

# IDs de precios de Stripe (se leen de config/env para poder usar
# price IDs reales en producción y test IDs en desarrollo)
_TIER_PRICE_IDS: dict[SubscriptionTier, str] = {
    SubscriptionTier.starter: settings.stripe_price_starter,
    SubscriptionTier.pro: settings.stripe_price_pro,
    SubscriptionTier.estudio: settings.stripe_price_estudio,
}

_PRICE_TO_TIER: dict[str, SubscriptionTier] = {
    v: k for k, v in _TIER_PRICE_IDS.items() if v
}


def _stripe():
    """Devuelve el módulo stripe inicializado. Falla limpio si no está configurado."""
    try:
        import stripe as _s
    except ImportError:
        raise RuntimeError("stripe no instalado; agregarlo a requirements.txt")
    if not settings.stripe_secret_key:
        raise RuntimeError("STRIPE_SECRET_KEY no configurada")
    _s.api_key = settings.stripe_secret_key
    return _s


def create_checkout_session(
    tenant: Tenant,
    tier: SubscriptionTier,
    success_url: str,
    cancel_url: str,
) -> str:
    """
    Crea una Stripe Checkout Session para suscribirse a un tier.
    Devuelve la URL a la que redirigir al usuario.
    """
    stripe = _stripe()
    price_id = _TIER_PRICE_IDS.get(tier)
    if not price_id:
        raise ValueError(f"No hay price_id configurado para el tier {tier}")

    # Crear o reutilizar el customer de Stripe
    customer_id = tenant.stripe_customer_id
    if not customer_id:
        customer = stripe.Customer.create(
            name=tenant.name,
            metadata={"tenant_id": str(tenant.id), "slug": tenant.slug},
        )
        customer_id = customer.id

    session_params: dict = {
        "customer": customer_id,
        "mode": "subscription",
        "line_items": [{"price": price_id, "quantity": 1}],
        "success_url": success_url,
        "cancel_url": cancel_url,
        "metadata": {"tenant_id": str(tenant.id)},
        "subscription_data": {
            "metadata": {"tenant_id": str(tenant.id)},
        },
    }

    # Trial: si el tenant está en período de trial, aplicarlo
    if tenant.trial_ends_at and tenant.trial_ends_at > datetime.utcnow():
        remaining_seconds = int((tenant.trial_ends_at - datetime.utcnow()).total_seconds())
        session_params["subscription_data"]["trial_period_days"] = max(1, remaining_seconds // 86400)

    session = stripe.checkout.Session.create(**session_params)
    return session.url


def create_portal_session(tenant: Tenant, return_url: str) -> str:
    """
    Crea una sesión del Customer Portal de Stripe para que el cliente
    gestione su suscripción (cancelar, cambiar plan, actualizar tarjeta).
    """
    stripe = _stripe()
    if not tenant.stripe_customer_id:
        raise ValueError("El tenant no tiene un customer de Stripe asociado")

    session = stripe.billing_portal.Session.create(
        customer=tenant.stripe_customer_id,
        return_url=return_url,
    )
    return session.url


def handle_webhook(payload: bytes, sig_header: str, db: Session) -> dict:
    """
    Procesa un webhook de Stripe y sincroniza el estado del tenant en DB.

    Eventos relevantes:
    - checkout.session.completed → asociar customer_id al tenant
    - customer.subscription.created / updated → actualizar tier y estado
    - customer.subscription.deleted → desactivar suscripción
    - invoice.payment_failed → marcar subscription como inactiva (grace period)
    """
    stripe = _stripe()
    if not settings.stripe_webhook_secret:
        raise ValueError("STRIPE_WEBHOOK_SECRET no configurada")

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, settings.stripe_webhook_secret
        )
    except stripe.error.SignatureVerificationError as e:
        raise ValueError(f"Firma de webhook inválida: {e}")

    event_type = event["type"]
    data = event["data"]["object"]

    logger.info(f"Stripe webhook: {event_type}")

    if event_type == "checkout.session.completed":
        _handle_checkout_completed(data, db)

    elif event_type in ("customer.subscription.created", "customer.subscription.updated"):
        _handle_subscription_updated(data, db)

    elif event_type == "customer.subscription.deleted":
        _handle_subscription_deleted(data, db)

    elif event_type == "invoice.payment_failed":
        _handle_payment_failed(data, db)

    return {"received": True, "event": event_type}


def _handle_checkout_completed(session: dict, db: Session):
    tenant_id = session.get("metadata", {}).get("tenant_id")
    customer_id = session.get("customer")
    subscription_id = session.get("subscription")
    if not tenant_id:
        return

    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    if not tenant:
        logger.warning(f"Tenant {tenant_id} no encontrado en checkout.session.completed")
        return

    tenant.stripe_customer_id = customer_id
    if subscription_id:
        tenant.stripe_subscription_id = subscription_id
    db.commit()


def _handle_subscription_updated(subscription: dict, db: Session):
    customer_id = subscription.get("customer")
    subscription_id = subscription.get("id")
    status = subscription.get("status")  # active, trialing, past_due, canceled

    tenant = db.query(Tenant).filter(Tenant.stripe_customer_id == customer_id).first()
    if not tenant:
        # Intentar por metadata
        tenant_id = subscription.get("metadata", {}).get("tenant_id")
        if tenant_id:
            tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    if not tenant:
        logger.warning(f"Tenant no encontrado para customer {customer_id}")
        return

    tenant.stripe_subscription_id = subscription_id
    tenant.subscription_active = status in ("active", "trialing")

    # Determinar tier desde el price_id del primer item
    items = subscription.get("items", {}).get("data", [])
    if items:
        price_id = items[0].get("price", {}).get("id")
        tier = _PRICE_TO_TIER.get(price_id)
        if tier:
            tenant.tier = tier

    # Sincronizar trial_end
    trial_end_ts = subscription.get("trial_end")
    if trial_end_ts:
        tenant.trial_ends_at = datetime.utcfromtimestamp(trial_end_ts)

    db.commit()
    logger.info(f"Tenant {tenant.slug}: tier={tenant.tier}, active={tenant.subscription_active}")


def _handle_subscription_deleted(subscription: dict, db: Session):
    customer_id = subscription.get("customer")
    tenant = db.query(Tenant).filter(Tenant.stripe_customer_id == customer_id).first()
    if not tenant:
        return
    tenant.subscription_active = False
    db.commit()
    logger.info(f"Tenant {tenant.slug}: suscripción cancelada")


def _handle_payment_failed(invoice: dict, db: Session):
    customer_id = invoice.get("customer")
    tenant = db.query(Tenant).filter(Tenant.stripe_customer_id == customer_id).first()
    if not tenant:
        return
    # No desactivar inmediatamente — Stripe reintenta; solo loguear
    logger.warning(f"Pago fallido para tenant {tenant.slug} (customer {customer_id})")
    # Notificar al admin
    from app.services.notifications.email import send_admin_health_alert
    send_admin_health_alert(
        f"Pago fallido para el tenant '{tenant.name}' (slug: {tenant.slug}). "
        "Verificar en el dashboard de Stripe."
    )
