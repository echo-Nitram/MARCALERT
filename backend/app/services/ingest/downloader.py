"""
Ingesta del Boletín de la Propiedad Industrial.

DOBLE VÍA (según spec):
1. Vía primaria: adivinar URL correlativa (ultimo_numero + 1).
2. Vía de respaldo: parsear índice HTML del año.

Health check: alertar al admin si la URL esperada sigue en 404 tras el margen
o devuelve un código inesperado (señal de cambio de estructura del sitio).
"""
from __future__ import annotations

import logging
import os
import tempfile
from datetime import date, datetime
from typing import Optional
from urllib.parse import quote

import httpx

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


def build_boletin_url(numero: int) -> str:
    """Construye la URL del PDF del boletín según el patrón CONFIRMADO de DNPI."""
    ministry = settings.boletin_pdf_ministry
    base = settings.dnpi_base_url
    # URL patrón: .../sites/{ministry}/files/.../Boletin%20{n}.pdf
    path = f"/sites/{ministry}/files/documentos/publicaciones/Boletin%20{numero}.pdf"
    return base + path


def build_index_url(year: int) -> str:
    base = settings.dnpi_base_url
    return f"{base}/comunicacion/publicaciones/boletin-propiedad-industrial-ano-{year}"


def check_boletin_exists(numero: int, timeout: float = 20.0) -> tuple[bool, int]:
    """
    Verifica si el boletín {numero} está disponible.
    Devuelve (existe, status_code).
    status_code:
      200 → existe
      404 → no publicado todavía
      otro → anomalía (notificar admin)
    """
    url = build_boletin_url(numero)
    try:
        with httpx.Client(follow_redirects=True, timeout=timeout) as client:
            resp = client.head(url)
            return resp.status_code == 200, resp.status_code
    except httpx.TimeoutException:
        logger.warning(f"Timeout al verificar boletín {numero}: {url}")
        return False, -1
    except Exception as e:
        logger.error(f"Error al verificar boletín {numero}: {e}")
        return False, -2


def download_boletin(numero: int, dest_dir: str, timeout: float = 120.0) -> Optional[str]:
    """
    Descarga el PDF del boletín {numero} a dest_dir.
    Devuelve la ruta al archivo o None si no está disponible.
    """
    url = build_boletin_url(numero)
    dest_path = os.path.join(dest_dir, f"boletin_{numero}.pdf")

    if os.path.exists(dest_path):
        logger.info(f"Boletín {numero} ya descargado: {dest_path}")
        return dest_path

    logger.info(f"Descargando boletín {numero} desde {url}")
    try:
        with httpx.Client(follow_redirects=True, timeout=timeout) as client:
            with client.stream("GET", url) as resp:
                if resp.status_code == 404:
                    return None
                resp.raise_for_status()
                with open(dest_path, "wb") as f:
                    for chunk in resp.iter_bytes(chunk_size=65536):
                        f.write(chunk)
        size = os.path.getsize(dest_path)
        logger.info(f"Boletín {numero} descargado: {size/1024:.1f} KB → {dest_path}")
        return dest_path
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            return None
        logger.error(f"Error HTTP descargando boletín {numero}: {e}")
        return None
    except Exception as e:
        logger.error(f"Error descargando boletín {numero}: {e}")
        return None


def scrape_index_for_number(year: int) -> Optional[int]:
    """
    Vía de respaldo: parsear el índice HTML del año para obtener el último número.
    Busca texto tipo "Boletín 359" en el HTML del índice.
    """
    import re
    url = build_index_url(year)
    try:
        with httpx.Client(follow_redirects=True, timeout=20.0) as client:
            resp = client.get(url)
            resp.raise_for_status()
    except Exception as e:
        logger.warning(f"No se pudo acceder al índice HTML {url}: {e}")
        return None

    numbers = [int(m.group(1)) for m in re.finditer(r"Bolet[íi]n\s*(\d{3,4})", resp.text)]
    return max(numbers) if numbers else None


def health_check_needed(ultimo_procesado: int, fecha_esperada: date, margen_dias: int = 2) -> bool:
    """
    Determina si se debe disparar el health check al admin.
    Condición: pasó fecha_esperada + margen y el siguiente número sigue en 404.
    """
    hoy = date.today()
    if hoy <= fecha_esperada:
        return False  # Todavía no es tarde
    dias_pasados = (hoy - fecha_esperada).days
    if dias_pasados < margen_dias:
        return False
    exists, status = check_boletin_exists(ultimo_procesado + 1)
    return not exists and status == 404
