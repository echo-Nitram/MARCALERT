"""
Calendario de días hábiles de Uruguay.

Usa el paquete `holidays` para los feriados nacionales.
Días no hábiles: sábado, domingo y feriados nacionales UY.

Funciones:
- is_business_day(d): ¿es día hábil?
- add_business_days(d, n): suma n días hábiles
- business_days_between(start, end): días hábiles entre dos fechas
- next_business_day_on_or_before(d): último hábil ≤ d (para scheduler)
- expected_boletin_dates(year): lista de fechas esperadas de boletines del año
"""
from __future__ import annotations

from datetime import date, timedelta
from typing import Optional

try:
    import holidays as holidays_lib
    _UY_HOLIDAYS = holidays_lib.Uruguay()
except ImportError:
    _UY_HOLIDAYS = {}  # fallback si no está instalado


def is_business_day(d: date) -> bool:
    return d.weekday() < 5 and d not in _UY_HOLIDAYS


def add_business_days(start: date, n: int) -> date:
    """Suma n días hábiles a start (inclusive el primero si es hábil)."""
    current = start
    counted = 0
    while counted < n:
        current += timedelta(days=1)
        if is_business_day(current):
            counted += 1
    return current


def business_days_between(start: date, end: date) -> int:
    """Días hábiles desde start (exclusive) hasta end (inclusive)."""
    count = 0
    current = start + timedelta(days=1)
    while current <= end:
        if is_business_day(current):
            count += 1
        current += timedelta(days=1)
    return count


def next_business_day_on_or_before(d: date) -> date:
    """
    Si d es hábil, devuelve d.
    Si no, retrocede hasta el último día hábil anterior.
    (Regla para publicación de boletines: si el 15 o fin de mes cae en no hábil,
    se publica el último hábil anterior.)
    """
    current = d
    while not is_business_day(current):
        current -= timedelta(days=1)
    return current


def expected_boletin_dates(year: int) -> list[date]:
    """
    Devuelve la lista de fechas esperadas de publicación de boletines para un año.
    Quincenal: día 15 y último día de cada mes, ajustado a último hábil anterior.
    """
    import calendar
    dates = []
    for month in range(1, 13):
        last_day = calendar.monthrange(year, month)[1]
        for day in (15, last_day):
            target = date(year, month, day)
            actual = next_business_day_on_or_before(target)
            dates.append(actual)
    # Eliminar duplicados (puede ocurrir si el 15 y el último día son adyacentes y no hábiles)
    return sorted(set(dates))


def next_expected_boletin_date(after: Optional[date] = None) -> date:
    """Devuelve la próxima fecha esperada de publicación después de `after`."""
    if after is None:
        after = date.today()
    for year in (after.year, after.year + 1):
        for d in expected_boletin_dates(year):
            if d > after:
                return d
    raise RuntimeError("No se pudo calcular próxima fecha de boletín")


def compute_oposicion_deadline(fecha_publicacion: date, dias_habiles: int = 30) -> date:
    """
    Calcula la fecha límite de oposición.
    DISCLAIMER: verificar contra Ley 17.011. Usar 30 días hábiles como estimado.
    """
    return add_business_days(fecha_publicacion, dias_habiles)
