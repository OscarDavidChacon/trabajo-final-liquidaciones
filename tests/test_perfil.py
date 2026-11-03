"""Pruebas de inventario, perfil y hallazgos con tablas pequeñas del test."""

import pandas as pd

from app.services.perfil import hallazgos, inventario, perfil_tabla


def _tablas_de_prueba():
    animales = pd.DataFrame({
        "liquidacion_id": ["1", "1", "1"],
        "Número": ["10", "10", "11"],
        "Canal": ["", "", ""],
        "Sexo": ["H", "H", "H"],
        "Arete": ["", "99", ""],
        "Peso Pie": ["300.00", "300.00", "-5.00"],
        "Peso Canal": ["200.00", "250.00", "100.00"],
        "Rendi %": ["60.0", "60.0", "120.0"],
        "Calif.": ["AA", "AA", "AA"],
        "Precio col.": ["2,000.00", "2,000.00", "2,000.00"],
        "Bono": ["25.00", "25.00", "25.00"],
        "Precio KG": ["2,025.00", "2,025.00", "2,025.00"],
        "Total colones": ["400,000.00", "400,000.00", "200,000.00"],
    })
    resumen = pd.DataFrame({
        "liquidacion_id": ["1"],
        "fecha": ["01/01/2026"],
        "cantidad": ["3"],
        "total_ingresos": ["1,000,000.00"],
    })
    return {"animales": animales, "resumen": resumen}


def test_inventario_cuenta_filas_y_columnas():
    inv = inventario(_tablas_de_prueba())
    resumen = {t["tabla"]: t for t in inv}
    assert resumen["animales"]["filas"] == 3
    assert resumen["animales"]["columnas"] == 13


def test_perfil_detecta_numericas_y_vacios():
    perfil = perfil_tabla(_tablas_de_prueba()["animales"])
    por_col = {c["columna"]: c for c in perfil}
    assert por_col["Canal"]["vacios"] == 3
    assert por_col["Arete"]["vacios"] == 2
    # "Total colones" viene como texto pero se puede interpretar como número
    assert por_col["Total colones"]["max"] == 400000.0


def test_hallazgos_detecta_familias_clave():
    h = hallazgos(_tablas_de_prueba())
    familias = {x["familia"] for x in h}
    assert "Tipo de dato incorrecto" in familias
    assert "Vacíos" in familias
    assert "Duplicados" in familias          # la llave 1+10 se repite
    assert "Fuera de rango o incoherente" in familias
    por_familia = {}
    for x in h:
        por_familia.setdefault(x["familia"], []).append(x)
    # duplicado exacto de llave -> 1
    assert any(x["cantidad"] == 1 for x in por_familia["Duplicados"])
    # pesos negativos y rendimiento > 100 -> al menos 1 fila marcada
    assert any(x["cantidad"] >= 1 for x in por_familia["Fuera de rango o incoherente"])
    # todos los hallazgos tienen id, tipo y cantidad
    assert all(x["id"].startswith("H") and x["tipo"] in ("Calidad", "Negocio") for x in h)
