"""
Tests unitarios del módulo de billing.
No llaman a Stripe real — testean la lógica de mapeo y configuración.
"""
import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime, timedelta

from app.models.tenant import Tenant, SubscriptionTier
from app.services.billing.stripe_service import _TIER_PRICE_IDS, _PRICE_TO_TIER


def make_tenant(**kwargs) -> Tenant:
    t = Tenant()
    t.id = "00000000-0000-0000-0000-000000000001"
    t.name = "Test Estudio"
    t.slug = "test-estudio"
    t.tier = SubscriptionTier.starter
    t.stripe_customer_id = None
    t.stripe_subscription_id = None
    t.trial_ends_at = None
    t.subscription_active = True
    t.draft_credits = 3
    for k, v in kwargs.items():
        setattr(t, k, v)
    return t


def test_tier_price_ids_keys():
    """Todos los tiers tienen una entrada en el mapa (aunque estén vacíos en test)."""
    for tier in SubscriptionTier:
        assert tier in _TIER_PRICE_IDS


def test_price_to_tier_inverse():
    """Si hay price IDs configurados, el mapa inverso es correcto."""
    for price_id, tier in _PRICE_TO_TIER.items():
        assert _TIER_PRICE_IDS[tier] == price_id


def test_handle_subscription_updated_sets_tier():
    """_handle_subscription_updated sincroniza el tier desde el price_id."""
    from app.services.billing.stripe_service import _handle_subscription_updated

    # Simular que el price_id de Starter está configurado
    starter_price = "price_starter_test"
    with patch.dict("app.services.billing.stripe_service._TIER_PRICE_IDS",
                    {SubscriptionTier.starter: starter_price}):
        with patch.dict("app.services.billing.stripe_service._PRICE_TO_TIER",
                        {starter_price: SubscriptionTier.starter}):

            tenant = make_tenant(stripe_customer_id="cus_test123")
            db = MagicMock()
            db.query.return_value.filter.return_value.first.return_value = tenant

            subscription = {
                "id": "sub_test",
                "customer": "cus_test123",
                "status": "active",
                "trial_end": None,
                "items": {"data": [{"price": {"id": starter_price}}]},
                "metadata": {},
            }
            _handle_subscription_updated(subscription, db)

            assert tenant.tier == SubscriptionTier.starter
            assert tenant.subscription_active is True
            db.commit.assert_called_once()


def test_handle_subscription_deleted_deactivates():
    from app.services.billing.stripe_service import _handle_subscription_deleted

    tenant = make_tenant(stripe_customer_id="cus_del")
    db = MagicMock()
    db.query.return_value.filter.return_value.first.return_value = tenant

    _handle_subscription_deleted({"customer": "cus_del"}, db)

    assert tenant.subscription_active is False
    db.commit.assert_called_once()


def test_handle_subscription_updated_trialing():
    from app.services.billing.stripe_service import _handle_subscription_updated

    future_ts = int((datetime.utcnow() + timedelta(days=15)).timestamp())
    tenant = make_tenant(stripe_customer_id="cus_trial")
    db = MagicMock()
    db.query.return_value.filter.return_value.first.return_value = tenant

    subscription = {
        "id": "sub_trial",
        "customer": "cus_trial",
        "status": "trialing",
        "trial_end": future_ts,
        "items": {"data": []},
        "metadata": {},
    }
    _handle_subscription_updated(subscription, db)

    assert tenant.subscription_active is True
    assert tenant.trial_ends_at is not None


def test_handle_subscription_updated_unknown_customer():
    from app.services.billing.stripe_service import _handle_subscription_updated

    db = MagicMock()
    db.query.return_value.filter.return_value.first.return_value = None

    # No debe lanzar excepción
    _handle_subscription_updated({
        "customer": "cus_unknown",
        "id": "sub_x",
        "status": "active",
        "trial_end": None,
        "items": {"data": []},
        "metadata": {},
    }, db)
    db.commit.assert_not_called()
