from datetime import datetime, date
import uuid
import enum

from sqlalchemy import Column, String, DateTime, Date, Integer, Text, Float, Boolean, ForeignKey, Enum as SAEnum
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship

from app.database import Base


class EstadoAlerta(str, enum.Enum):
    nueva = "nueva"
    revisada = "revisada"
    en_oposicion = "en_oposicion"
    descartada = "descartada"


class Alerta(Base):
    """Colisión detectada entre una solicitud del boletín y una marca vigilada."""
    __tablename__ = "alertas"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    marca_vigilada_id = Column(UUID(as_uuid=True), ForeignKey("marcas_vigiladas.id", ondelete="CASCADE"), nullable=False, index=True)
    solicitud_id = Column(UUID(as_uuid=True), ForeignKey("solicitudes.id", ondelete="CASCADE"), nullable=False, index=True)

    # Scores del embudo
    score_denominativo = Column(Float, nullable=False)     # capa A
    score_clase = Column(Float, nullable=False)            # capa A
    score_total = Column(Float, nullable=False)            # combinación final
    score_figurativo = Column(Float, nullable=True)        # capa C (solo si aplica)

    # Detalle del matching
    detalle_fonetico = Column(JSONB, nullable=True)        # {'metodo': 'levenshtein', 'distancia': 2, ...}
    explicacion_ia = Column(Text, nullable=True)           # capa B: texto generado por Claude

    # Plazo de oposición
    fecha_limite_oposicion = Column(Date, nullable=True)
    dias_habiles_restantes = Column(Integer, nullable=True)

    estado = Column(SAEnum(EstadoAlerta), nullable=False, default=EstadoAlerta.nueva)
    notificado_email = Column(Boolean, default=False)
    notificado_telegram = Column(Boolean, default=False)

    # Feature premium: borrador de oposición
    borrador_oposicion = Column(Text, nullable=True)
    borrador_generado_at = Column(DateTime, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    tenant = relationship("Tenant", back_populates="alertas")
    marca_vigilada = relationship("MarcaVigilada", back_populates="alertas")
    solicitud = relationship("Solicitud", back_populates="alertas")


class MetricaBoletin(Base):
    """Métricas por boletín por tenant (para retención y argumento de venta)."""
    __tablename__ = "metricas_boletin"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    boletin_numero = Column(Integer, nullable=False)
    total_solicitudes_analizadas = Column(Integer, nullable=False, default=0)
    total_colisiones_detectadas = Column(Integer, nullable=False, default=0)
    total_descartadas = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
