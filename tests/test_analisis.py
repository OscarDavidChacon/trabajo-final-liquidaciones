"""Pruebas del análisis (P1, P2, P3) con archivos pequeños creados en el test."""

import pytest

from app.services.analisis import (analisis_completo, cargar_base, control,
                                   distribuciones, kpis, p1, p2, p3)

BASE = (
    "liquidacion_id,Número,Peso Pie,Peso Canal,Rendi %,Calif.,Precio KG,Total colones,marcas\n"
    "1,10,300.0,200.0,66.7,AA,2025.0,400000.0,R5:canal\n"
    "1,11,250.0,150.0,60.0,AAA,2025.0,300000.0,R5:canal\n"
    "2,20,200.0,120.0,60.0,A,2000.0,250000.0,\n"
)
RESUMEN_2MESES = (
    "liquidacion_id,fecha,total_materia_prima,total_bonos,total_ingresos,iva,subtotal,"
    "total_deducciones,total_neto_a_pagar\n"
    "1,15/01/2026,690000.0,10000.0,700000.0,7000.0,707000.0,7000.0,700000.0\n"
    "2,15/02/2026,245000.0,5000.0,250000.0,2500.0,252500.0,4500.0,248000.0\n"
)
RESUMEN_1MES = (
    "liquidacion_id,fecha,total_materia_prima,total_bonos,total_ingresos,iva,subtotal,"
    "total_deducciones,total_neto_a_pagar\n"
    "1,15/01/2026,690000.0,10000.0,700000.0,7000.0,707000.0,7000.0,700000.0\n"
)


def _escribir(tmp_path, resumen=RESUMEN_2MESES):
    (tmp_path / "base_limpia.csv").write_text(BASE, encoding="utf-8-sig")
    (tmp_path / "liquidacion_resumen.csv").write_text(resumen, encoding="utf-8-sig")
    return tmp_path


def test_error_claro_si_falta_base(tmp_path):
    with pytest.raises(FileNotFoundError, match="base_limpia.csv"):
        cargar_base(tmp_path)


def test_kpis(tmp_path):
    base = cargar_base(_escribir(tmp_path))
    k = kpis(base)
    assert k["filas_universo"] == 3
    assert k["suma_total_colones"] == 950000.0
    assert k["liquidaciones_unicas"] == 2
    assert k["pct_filas_marcadas"] == pytest.approx(66.67, abs=0.01)


def test_p1_identidades(tmp_path):
    ruta = _escribir(tmp_path)
    base = cargar_base(ruta)
    from app.services.analisis import cargar_resumen
    resultado = p1(base, cargar_resumen(ruta))
    assert all(x["identidades_ok"] for x in resultado["por_liquidacion"])
    assert resultado["totales"]["neto_a_pagar"] == 948000.0


def test_p2_pareto_acumula_100(tmp_path):
    base = cargar_base(_escribir(tmp_path))
    r = p2(base)
    assert r["total_colones"] == 950000.0
    assert r["n_animales"] == 3
    assert r["top_por_valor"][0]["Número"] == "10"
    assert r["top_por_valor"][-1]["pct_acumulado"] == pytest.approx(100.0, abs=0.01)
    assert r["por_clasificacion"] == {"AA": 1, "AAA": 1, "A": 1}


def test_p3_insuficiente_con_un_mes(tmp_path):
    ruta = _escribir(tmp_path, RESUMEN_1MES)
    base = cargar_base(ruta)
    from app.services.analisis import cargar_resumen
    r = p3(base, cargar_resumen(ruta))
    assert r["disponible"] is False


def test_p3_disponible_con_dos_meses(tmp_path):
    ruta = _escribir(tmp_path)
    base = cargar_base(ruta)
    from app.services.analisis import cargar_resumen
    r = p3(base, cargar_resumen(ruta))
    assert r["disponible"] is True
    assert len(r["serie"]) == 2


def test_distribuciones_y_control(tmp_path):
    ruta = _escribir(tmp_path)
    base = cargar_base(ruta)
    from app.services.analisis import cargar_resumen
    resumen = cargar_resumen(ruta)
    dist = distribuciones(base)
    assert dist["cuartiles"]["p50"] == 300000.0
    assert len(dist["histograma"]["conteos"]) == 20
    ctrl = control(base, resumen)
    assert ctrl["disponible"] is True
    assert "limite_superior" in ctrl


def test_analisis_completo_serializable(tmp_path):
    import json
    resultado = analisis_completo(_escribir(tmp_path))
    assert set(resultado) == {"kpis", "p1", "p2", "p3", "distribuciones", "control"}
    json.dumps(resultado)  # no debe lanzar
