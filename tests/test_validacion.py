"""Pruebas de cifras de control y veredicto (tablas del test, sin API)."""

import pandas as pd

from app.services.limpieza import limpiar
from app.services.validacion import cifras_control, validar

LLAVE = ["liquidacion_id", "Número"]


def _tablas(con_duplicado=False):
    filas = [
        ("1", "10", "300.00", "200.00", "60.0"),
        ("1", "11", "250.00", "150.00", "60.0"),
    ]
    if con_duplicado:
        filas.append(("1", "10", "300.00", "200.00", "60.0"))
    animales = pd.DataFrame({
        "liquidacion_id": [f[0] for f in filas],
        "Número": [f[1] for f in filas],
        "Canal": [""] * len(filas),
        "Sexo": ["H"] * len(filas),
        "Arete": [""] * len(filas),
        "Peso Pie": [f[2] for f in filas],
        "Peso Canal": [f[3] for f in filas],
        "Rendi %": [f[4] for f in filas],
        "Calif.": ["AA"] * len(filas),
        "Precio col.": ["2,000.00"] * len(filas),
        "Bono": ["25.00"] * len(filas),
        "Precio KG": ["2,025.00"] * len(filas),
        "Total colones": ["400,000.00", "300,000.00"] + (["400,000.00"] if con_duplicado else []),
    })
    resumen = pd.DataFrame({
        "liquidacion_id": ["1"],
        "fecha": ["01/01/2026"],
        "fecha_matanza": ["02/01/2026"],
        "cantidad": ["2"],
        "total_materia_prima": ["690,000.00"],
        "total_bonos": ["10,000.00"],
        "total_ingresos": ["700,000.00"],
        "iva": ["7,000.00"],
        "subtotal": ["707,000.00"],
        "total_deducciones": ["7,000.00"],
        "total_neto_a_pagar": ["700,000.00"],
    })
    return {"animales": animales, "resumen": resumen}


def test_cifras_control():
    c = cifras_control(_tablas())
    assert c["filas"] == 2
    assert c["llaves_unicas"] == 2
    assert c["suma_total_colones"] == 700000.0


def test_veredicto_aprobado():
    tablas = _tablas()
    resultado = validar(tablas, limpiar(tablas))
    assert resultado["veredicto"] == "APROBADO"
    assert all(p["ok"] for p in resultado["pruebas"])


def test_veredicto_rechazado_si_hay_llave_duplicada():
    # simula que la regla de Eliminar está desactivada: la base conserva la llave repetida
    tablas = _tablas(con_duplicado=True)
    base = tablas["animales"].copy()
    resultado = validar(tablas, {"base": base, "eliminados": []})
    assert resultado["veredicto"] == "RECHAZADO"
    assert any(p["prueba"].startswith("liquidacion_id + Número única") and not p["ok"]
               for p in resultado["pruebas"])


def test_diferencia_de_filas_explicada_por_r3():
    tablas = _tablas(con_duplicado=True)
    resultado = validar(tablas, limpiar(tablas))
    fila = next(f for f in resultado["tabla"] if f["metrica"] == "Filas de detalle")
    assert fila["diferencia"] == -1
    assert "R3" in fila["explicacion"]
