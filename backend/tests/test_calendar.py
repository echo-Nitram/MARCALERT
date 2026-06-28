"""
Tests del calendario hábil uruguayo.
"""
import pytest
from datetime import date
from app.services.calendar.uruguay import (
    is_business_day,
    add_business_days,
    business_days_between,
    next_business_day_on_or_before,
    expected_boletin_dates,
    compute_oposicion_deadline,
)


def test_sabado_no_habil():
    saturday = date(2026, 6, 27)  # sábado
    assert not is_business_day(saturday)


def test_domingo_no_habil():
    sunday = date(2026, 6, 28)  # domingo
    assert not is_business_day(sunday)


def test_lunes_habil():
    monday = date(2026, 6, 29)  # lunes
    assert is_business_day(monday)


def test_add_business_days():
    start = date(2026, 6, 15)  # lunes (si es hábil)
    result = add_business_days(start, 5)
    # 5 días hábiles desde el 15 de junio
    assert result > start
    # No debe caer en fin de semana
    assert result.weekday() < 5


def test_business_days_between():
    start = date(2026, 6, 15)
    end = date(2026, 6, 22)  # 7 días calendario = 5 hábiles (lun-vie)
    count = business_days_between(start, end)
    assert 4 <= count <= 5  # según feriados


def test_next_business_day_on_or_before_habil():
    d = date(2026, 6, 15)  # lunes
    assert next_business_day_on_or_before(d) == d


def test_next_business_day_on_or_before_fin_semana():
    d = date(2026, 6, 27)  # sábado → vuelve al viernes 26
    result = next_business_day_on_or_before(d)
    assert result == date(2026, 6, 26)


def test_expected_boletin_dates_2026():
    dates = expected_boletin_dates(2026)
    assert len(dates) >= 20  # al menos 20 boletines al año (2 por mes × 12 - ajustes)
    # Todos los días deben ser hábiles
    for d in dates:
        assert is_business_day(d), f"{d} no es día hábil"


def test_compute_oposicion_deadline():
    fecha_pub = date(2026, 6, 15)
    deadline = compute_oposicion_deadline(fecha_pub, 30)
    count = business_days_between(fecha_pub, deadline)
    assert count == 30
