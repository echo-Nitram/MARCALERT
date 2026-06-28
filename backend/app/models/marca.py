from datetime import datetime
import uuid
import enum

from sqlalchemy import Column, String, DateTime, Integer, Text, LargeBinary, Enum as SAEnum, ForeignKey, ARRAY
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.database import Base


class SensibilidadUmbral(str, enum.Enum):
    bajo = "bajo"      # score >= 60
    medio = "medio"    # score >= 75
    alto = "alto"      # score >= 90


class TipoMarca(str, enum.Enum):
    denominativa = "denominativa"
    figurativa = "figurativa"
    mixta = "mixta"


class MarcaVigilada(Base):
    """Marca en la cartera de un agente (lo que se vigila)."""
    __tablename__ = "marcas_vigiladas"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    denominacion = Column(String(500), nullable=False)
    tipo = Column(SAEnum(TipoMarca), nullable=False, default=TipoMarca.denominativa)
    # clases Niza como array de enteros (ej. [30, 35])
    clases_niza = Column(ARRAY(Integer), nullable=False, default=list)
    logo_path = Column(String(500), nullable=True)
    logo_data = Column(LargeBinary, nullable=True)
    logo_mime = Column(String(50), nullable=True)
    sensibilidad = Column(SAEnum(SensibilidadUmbral), nullable=False, default=SensibilidadUmbral.medio)
    cliente_nombre = Column(String(500), nullable=True)  # cliente final del agente
    notas = Column(Text, nullable=True)
    activa = Column(Integer, nullable=False, default=1)  # 1=activa, 0=pausada
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    tenant = relationship("Tenant", back_populates="marcas")
    alertas = relationship("Alerta", back_populates="marca_vigilada", cascade="all, delete-orphan")

    @property
    def score_threshold(self) -> int:
        thresholds = {
            SensibilidadUmbral.bajo: 60,
            SensibilidadUmbral.medio: 75,
            SensibilidadUmbral.alto: 90,
        }
        return thresholds[self.sensibilidad]
