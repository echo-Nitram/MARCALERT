from app.models.tenant import Tenant
from app.models.user import User
from app.models.marca import MarcaVigilada
from app.models.boletin import Boletin, Solicitud
from app.models.alerta import Alerta

__all__ = [
    "Tenant",
    "User",
    "MarcaVigilada",
    "Boletin",
    "Solicitud",
    "Alerta",
]
