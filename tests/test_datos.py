"""Pruebas de carga de tablas (tablas pequeñas creadas en el propio test)."""

from pathlib import Path

import pytest

from app.models.datos import cargar_tablas

ANIMALES = "liquidacion_id,Número,Canal,Sexo,Arete,Peso Pie,Total colones\n123,1000,,H,,300.00,\"1,000.00\"\n"
RESUMEN = "liquidacion_id,fecha,cantidad,total_ingresos\n123,01/01/2026,1,\"1,000.00\"\n"


def _escribir(tmp_path):
    (tmp_path / "liquidacion_animales.csv").write_text(ANIMALES, encoding="utf-8-sig")
    (tmp_path / "liquidacion_resumen.csv").write_text(RESUMEN, encoding="utf-8-sig")
    return tmp_path


def test_carga_las_dos_tablas(tmp_path):
    tablas = cargar_tablas(_escribir(tmp_path))
    assert set(tablas) == {"animales", "resumen"}
    assert len(tablas["animales"]) == 1
    assert len(tablas["resumen"]) == 1


def test_error_claro_si_falta_archivo(tmp_path):
    _escribir(tmp_path)
    (tmp_path / "liquidacion_resumen.csv").unlink()
    with pytest.raises(FileNotFoundError) as exc:
        cargar_tablas(tmp_path)
    assert "liquidacion_resumen.csv" in str(exc.value)
