from datetime import datetime
import uuid
import enum

from sqlalchemy import Column, String, DateTime, Boolean, Integer, Enum as SAEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.database import Base


class SubscriptionTier(str, enum.Enum):
    starter = "starter"    # hasta 10 marcas, USD 29/mes
    pro = "pro"            # hasta 50 marcas, USD 79/mes
    estudio = "estudio"    # ilimitadas + borradores, USD 199/mes


class Tenant(Base):
    __tablename__ = "tenants"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    slug = Column(String(100), unique=True, nullable=False)
    tier = Column(SAEnum(SubscriptionTier), nullable=False, default=SubscriptionTier.starter)
    stripe_customer_id = Column(String(255), nullable=True)
    stripe_subscription_id = Column(String(255), nullable=True)
    trial_ends_at = Column(DateTime, nullable=True)
    subscription_active = Column(Boolean, nullable=False, default=True)
    draft_credits = Column(Integer, nullable=False, default=3)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    users = relationship("User", back_populates="tenant", cascade="all, delete-orphan")
    marcas = relationship("MarcaVigilada", back_populates="tenant", cascade="all, delete-orphan")
    alertas = relationship("Alerta", back_populates="tenant", cascade="all, delete-orphan")
