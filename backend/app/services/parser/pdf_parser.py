"""
Parser del Boletín de la Propiedad Industrial (DNPI/MIEM).

Estructura del PDF (CONFIRMADO en boletines reales):
- PDF de texto seleccionable (no escaneado).
- Portada con fecha oficial: "N°359 15/06/2026".
- Páginas iniciales: tabla de agentes (a saltear).
- Cuerpo: registros INID separados por marcador (210).
- Logos: imágenes embebidas; la mayoría son ruido vectorial de área ~0.46 pt².
"""
from __future__ import annotations

import io
import re
import logging
from dataclasses import dataclass, field
from datetime import date
from typing import Optional

logger = logging.getLogger(__name__)

# Regex de portada: "N°359 15/06/2026" o "Nº 359, 15/06/2026"
_RE_PORTADA = re.compile(
    r"N[°º]\.?\s*(\d+)[,\s]+(\d{1,2})[/\-\.](\d{1,2})[/\-\.](\d{4})",
    re.IGNORECASE,
)

# Marcadores INID relevantes
_RE_210 = re.compile(r"\(210\)\s*(.+?)(?=\n|\(2[12]\d\)|\(5[0-9]{2}\)|\(7[0-9]{2}\)|$)", re.DOTALL)
_RE_540 = re.compile(r"\(540\)\s*(.*?)(?=\n\s*\(|\Z)", re.DOTALL)
_RE_730 = re.compile(r"\(730\)\s*(.*?)(?=\n\s*\(|\Z)", re.DOTALL)
_RE_220 = re.compile(r"\(220\)\s*(\d{1,2}[/\-\.]\d{1,2}[/\-\.]\d{4})")
_RE_511 = re.compile(r"\(511\)\s*(.*?)(?=\n\s*\(|\Z)", re.DOTALL)
_RE_740 = re.compile(r"\(740\)\s*(.*?)(?=\n\s*\(|\Z)", re.DOTALL)
_RE_591 = re.compile(r"\(591\)\s*(.*?)(?=\n\s*\(|\Z)", re.DOTALL)

# Fecha en formato UY
_RE_DATE = re.compile(r"(\d{1,2})[/\-\.](\d{1,2})[/\-\.](\d{4})")

# Detectar la página donde empieza el cuerpo de marcas
# El cuerpo empieza cuando hay al menos un marcador (210)
_RE_BODY_START = re.compile(r"\(210\)")


@dataclass
class SolicitudExtraida:
    expediente: str
    denominacion: Optional[str] = None
    solicitante: Optional[str] = None
    pais_solicitante: Optional[str] = None
    fecha_presentacion: Optional[date] = None
    clases_niza: list[int] = field(default_factory=list)
    agente_direccion: Optional[str] = None
    colores_reivindicados: Optional[str] = None
    pagina: Optional[int] = None
    raw_block: Optional[str] = None
    # Logo info (asociado por proximidad en la etapa de extracción de imágenes)
    logo_data: Optional[bytes] = None
    logo_mime: Optional[str] = None
    logo_width_pt: Optional[float] = None
    logo_height_pt: Optional[float] = None
    parsed_by_ai: bool = False


@dataclass
class BoletinExtraido:
    numero: int
    fecha_publicacion: date
    solicitudes: list[SolicitudExtraida] = field(default_factory=list)
    paginas: int = 0


def parse_boletin(pdf_path: str) -> BoletinExtraido:
    """Punto de entrada: parsea el PDF y devuelve el boletín con sus solicitudes."""
    try:
        import pdfplumber
    except ImportError:
        raise RuntimeError("pdfplumber no disponible; instalar con pip install pdfplumber")

    with pdfplumber.open(pdf_path) as pdf:
        total_pages = len(pdf.pages)
        logger.info(f"Abriendo PDF: {total_pages} páginas")

        # 1. Parsear portada (páginas 0–2 como máximo)
        numero, fecha_pub = _parse_portada(pdf)
        if numero is None:
            raise ValueError("No se encontró número de boletín en la portada")

        # 2. Extraer imágenes de todo el PDF (logos)
        logo_map = _extract_logos(pdf)

        # 3. Localizar primera página del cuerpo de marcas
        body_start_page = _find_body_start(pdf)
        logger.info(f"Cuerpo de marcas empieza en página {body_start_page + 1}")

        # 4. Concatenar texto del cuerpo y parsear bloques INID
        solicitudes = _parse_body(pdf, body_start_page, logo_map)

        return BoletinExtraido(
            numero=numero,
            fecha_publicacion=fecha_pub,
            solicitudes=solicitudes,
            paginas=total_pages,
        )


def _parse_portada(pdf) -> tuple[Optional[int], Optional[date]]:
    """Extrae el número y fecha oficial del boletín de la portada (primeras 3 páginas)."""
    for page in pdf.pages[:3]:
        text = page.extract_text() or ""
        m = _RE_PORTADA.search(text)
        if m:
            numero = int(m.group(1))
            day, month, year = int(m.group(2)), int(m.group(3)), int(m.group(4))
            return numero, date(year, month, day)
    return None, None


def _find_body_start(pdf) -> int:
    """Devuelve el índice (0-based) de la primera página con registros (210)."""
    # Las primeras páginas son portada + tabla de agentes (típicamente < 10 páginas)
    for i, page in enumerate(pdf.pages):
        text = page.extract_text() or ""
        if _RE_BODY_START.search(text):
            return i
    return 0


def _extract_logos(pdf) -> dict[tuple[int, float], tuple[bytes, str, float, float]]:
    """
    Extrae logos reales descartando ruido vectorial.

    Regla (CONFIRMADO): los logos reales tienen área grande (~100×33 pt);
    los fragmentos vectoriales son ~1×0.5 pt (área ≈ 0.46 pt²).
    Usar config.logo_min_area_pt2 como umbral.

    Devuelve dict keyed por (page_index, y_top_pt) → (bytes, mime, w, h)
    """
    from app.config import get_settings
    settings = get_settings()
    min_area = settings.logo_min_area_pt2

    logos: dict[tuple[int, float], tuple[bytes, str, float, float]] = {}

    for page_idx, page in enumerate(pdf.pages):
        images = page.images or []
        for img in images:
            w = img.get("width", 0)
            h = img.get("height", 0)
            area = w * h
            if area < min_area:
                continue  # ruido vectorial

            # Extraer bytes de la imagen
            img_data = _get_image_bytes(page, img)
            if img_data is None:
                continue

            y_top = img.get("top", 0)
            logos[(page_idx, y_top)] = (img_data, "image/png", w, h)

    logger.info(f"Logos reales extraídos: {len(logos)}")
    return logos


def _get_image_bytes(page, img_meta: dict) -> Optional[bytes]:
    """Extrae los bytes de una imagen del PDF usando pdfplumber/PIL."""
    try:
        from PIL import Image as PILImage

        # pdfplumber expone crop + to_image para recortes de región
        x0 = img_meta.get("x0", 0)
        y0 = img_meta.get("top", 0)
        x1 = img_meta.get("x1", x0 + img_meta.get("width", 1))
        y1 = img_meta.get("bottom", y0 + img_meta.get("height", 1))

        cropped = page.crop((x0, y0, x1, y1))
        pil_img = cropped.to_image(resolution=150).original
        buf = io.BytesIO()
        pil_img.save(buf, format="PNG")
        return buf.getvalue()
    except Exception as e:
        logger.debug(f"Error extrayendo imagen: {e}")
        return None


def _parse_body(
    pdf,
    start_page: int,
    logo_map: dict,
) -> list[SolicitudExtraida]:
    """Parsea el cuerpo de marcas del PDF y asocia logos."""
    from app.config import get_settings
    settings = get_settings()
    max_gap = settings.logo_proximity_max_gap_pt

    solicitudes: list[SolicitudExtraida] = []

    # Construir texto page-aware para poder rastrear páginas de cada registro
    page_texts: list[tuple[int, str]] = []
    for i, page in enumerate(pdf.pages):
        if i < start_page:
            continue
        text = page.extract_text() or ""
        page_texts.append((i, text))

    # Concatenar con marcadores de página para rastrear nº de pág
    full_text = ""
    page_offsets: list[tuple[int, int]] = []  # (char_offset, page_index)
    for page_idx, text in page_texts:
        page_offsets.append((len(full_text), page_idx))
        full_text += text + "\n"

    def char_to_page(char_pos: int) -> int:
        page = 0
        for offset, pidx in page_offsets:
            if char_pos >= offset:
                page = pidx
            else:
                break
        return page

    # Partir el texto en bloques usando (210) como separador
    # Cada bloque comienza en (210) y termina justo antes del siguiente (210)
    splits = list(re.finditer(r"\(210\)", full_text))
    if not splits:
        logger.warning("No se encontraron registros (210) en el cuerpo del PDF")
        return solicitudes

    for i, match in enumerate(splits):
        start = match.start()
        end = splits[i + 1].start() if i + 1 < len(splits) else len(full_text)
        block = full_text[start:end]
        page_num = char_to_page(start)

        sol = _parse_block(block, page_num)
        if sol:
            # Asociar logo por proximidad en la misma página (y_top más cercano)
            _assign_logo(sol, page_num, logo_map, max_gap)
            solicitudes.append(sol)

    logger.info(f"Solicitudes extraídas: {len(solicitudes)}")
    return solicitudes


def _parse_block(block: str, page_num: int) -> Optional[SolicitudExtraida]:
    """Parsea un bloque INID individual."""
    # Extraer expediente (210)
    m_210 = re.match(r"\(210\)\s*(\d+)", block)
    if not m_210:
        return None
    expediente = m_210.group(1).strip()

    sol = SolicitudExtraida(expediente=expediente, pagina=page_num + 1, raw_block=block)

    # (540) denominación
    m = _RE_540.search(block)
    if m:
        sol.denominacion = _clean(m.group(1))

    # (730) solicitante y país
    m = _RE_730.search(block)
    if m:
        raw730 = _clean(m.group(1))
        # Separar país: al final suele venir "; UY" o similar
        parts = raw730.rsplit(";", 1)
        sol.solicitante = parts[0].strip()
        if len(parts) == 2:
            sol.pais_solicitante = parts[1].strip()

    # (220) fecha de presentación
    m = _RE_220.search(block)
    if m:
        sol.fecha_presentacion = _parse_date(m.group(1))

    # (511) clases de Niza
    m = _RE_511.search(block)
    if m:
        sol.clases_niza = _parse_clases(m.group(1))

    # (740) dirección/agente
    m = _RE_740.search(block)
    if m:
        sol.agente_direccion = _clean(m.group(1))

    # (591) colores
    m = _RE_591.search(block)
    if m:
        sol.colores_reivindicados = _clean(m.group(1))

    return sol


def _assign_logo(
    sol: SolicitudExtraida,
    page_idx: int,
    logo_map: dict,
    max_gap: float,
) -> None:
    """Asigna el logo más próximo verticalmente al registro en la misma página."""
    candidates = [(y_top, data) for (pidx, y_top), data in logo_map.items() if pidx == page_idx]
    if not candidates:
        return
    # Tomar el logo con menor y_top (primero desde arriba) dentro del gap permitido
    candidates.sort(key=lambda x: x[0])
    best_y, best_data = candidates[0]
    if best_data:
        sol.logo_data, sol.logo_mime, sol.logo_width_pt, sol.logo_height_pt = best_data


def _clean(text: str) -> str:
    """Normaliza whitespace del texto extraído."""
    return re.sub(r"\s+", " ", text or "").strip()


def _parse_date(s: str) -> Optional[date]:
    m = _RE_DATE.match(s.strip())
    if not m:
        return None
    try:
        return date(int(m.group(3)), int(m.group(2)), int(m.group(1)))
    except ValueError:
        return None


def _parse_clases(s: str) -> list[int]:
    """Extrae lista de clases Niza de texto como '35 (S/D) y 43 (S/D)'."""
    return [int(x) for x in re.findall(r"\b([1-9]\d?)\b", s) if 1 <= int(x) <= 45]
