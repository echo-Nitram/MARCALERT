from datetime import datetime, date
import uuid

from sqlalchemy import Column, String, DateTime, Date, Integer, Text, LargeBinary, Boolean, Float, ForeignKey, ARRAY
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship

from app.database import Base


class Boletin(Base):
    """Registro de cada boletín procesado."""
    __tablename__ = "boletines"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    numero = Column(Integer, unique=True, nullable=False, index=True)
    fecha_publicacion = Column(Date, nullable=False)  # fecha oficial del boletín (portada)
    pdf_url = Column(String(500), nullable=False)
    pdf_size_bytes = Column(Integer, nullable=True)
    paginas = Column(Integer, nullable=True)
    total_solicitudes = Column(Integer, nullable=True)
    procesado = Column(Boolean, nullable=False, default=False)
    procesado_at = Column(DateTime, nullable=True)
    error_msg = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    solicitudes = relationship("Solicitud", back_populates="boletin", cascade="all, delete-orphan")


class Solicitud(Base):
    """Una solicitud de marca publicada en un boletín (lo que se compara)."""
    __tablename__ = "solicitudes"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    boletin_id = Column(UUID(as_uuid=True), ForeignKey("boletines.id", ondelete="CASCADE"), nullable=False, index=True)
    boletin_numero = Column(Integer, nullable=False, index=True)

    # Campos INID
    expediente = Column(String(50), nullable=False, index=True)  # (210)
    denominacion = Column(String(500), nullable=True)            # (540) texto
    solicitante = Column(String(500), nullable=True)             # (730)
    pais_solicitante = Column(String(10), nullable=True)
    fecha_presentacion = Column(Date, nullable=True)             # (220)
    clases_niza = Column(ARRAY(Integer), nullable=True)          # (511)
    agente_direccion = Column(Text, nullable=True)               # (740)
    colores_reivindicados = Column(String(500), nullable=True)   # (591)
    pagina_boletin = Column(Integer, nullable=True)

    # Logo extraído
    logo_data = Column(LargeBinary, nullable=True)   # bytes de la imagen
    logo_mime = Column(String(50), nullable=True)    # image/png, image/jpeg, etc.
    logo_width_pt = Column(Float, nullable=True)
    logo_height_pt = Column(Float, nullable=True)

    # Metadata de extracción
    raw_block = Column(Text, nullable=True)          # texto crudo del bloque INID
    parsed_by_ai = Column(Boolean, default=False)    # True si usó fallback IA

    created_at = Column(DateTime, default=datetime.utcnow)

    boletin = relationship("Boletin", back_populates="solicitudes")
    alertas = relationship("Alerta", back_populates="solicitud", cascade="all, delete-orphan")
