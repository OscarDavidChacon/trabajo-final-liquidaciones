"""Pruebas de limpieza (tablas pequeñas hechas en el test, sin API ni Insumos)."""

import pandas as pd

from app.services.limpieza import limpiar, normalizar_texto


def _tablas():
    animales = pd.DataFrame({
        "liquidacion_id": ["1", "1", "1", "2"],
        "Número": ["10", "10", "11", "20"],
        "Canal": ["", "", "", ""],
        "Sexo": ["H", "H", "H", "H"],
        "Arete": ["", "", "99", ""],
        "Peso Pie": ["300.00", "300.00", "-5.00", "200.00"],
        "Peso Canal": ["200.00", "200.00", "100.00", "150.00"],
        "Rendi %": ["60.0", "60.0", "120.0", "75.0"],
        "Calif.": ["AA", "AA", "AA", "AA"],
        "Precio col.": ["2,000.00", "2,000.00", "2,000.00", "2,000.00"],
        "Bono": ["25.00", "25.00", "25.00", "25.00"],
        "Precio KG": ["2,025.00", "2,025.00", "2,025.00", "2,025.00"],
        "Total colones": ["400,000.00", "400,000.00", "200,000.00", "300,000.00"],
    })
    resumen = pd.DataFrame({
        "liquidacion_id": ["1", "2"],
        "fecha": ["01/01/2026", "02/01/2026"],
        "fecha_matanza": ["02/01/2026", "03/01/2026"],
        "total_ingresos": ["600,000.00", "300,000.00"],
        "iva": ["6,000.00", "3,000.00"],
        "total_deducciones": ["1,000.00", "500.00"],
        "total_neto_a_pagar": ["605,000.00", "302,500.00"],
    })
    return {"animales": animales, "resumen": resumen}


def test_no_muta_las_tablas_originales():
    tablas = _tablas()
    antes = tablas["animales"].copy()
    limpiar(tablas)
    pd.testing.assert_frame_equal(tablas["animales"], antes)


def test_r2_convierte_numericos():
    base = limpiar(_tablas())["base"]
    assert base["Total colones"].dtype.kind == "f"
    assert base["Total colones"].max() == 400000.0


def test_r3_elimina_duplicado_exacto():
    resultado = limpiar(_tablas())
    # la fila (1,10) estaba dos veces y era idéntica -> queda 1
    assert len(resultado["eliminados"]) == 1
    assert len(resultado["base"]) == 3


def test_r4_y_r5_marcan():
    base = limpiar(_tablas())["base"]
    marcadas = base["marcas"].str.contains("R4:peso").any()
    assert marcadas  # hay peso negativo y rendimiento > 100
    assert base["marcas"].str.contains("R5:canal").all()  # Canal no confirmado
    assert base["marcas"].str.contains("R5:arete").any()


def test_bitacora_tiene_una_fila_por_regla():
    bitacora = limpiar(_tablas())["bitacora"]
    assert [b["regla"] for b in bitacora] == ["R1", "R2", "R3", "R4", "R5", "R6"]
    assert all("filas_afectadas" in b for b in bitacora)


def test_base_una_fila_por_llave():
    base = limpiar(_tablas())["base"]
    assert not base.duplicated(subset=["liquidacion_id", "Número"]).any()


def test_normalizar_texto():
    serie = pd.Series(["  Hembra ", "MACHO   grande", "Categoría"])
    assert list(normalizar_texto(serie)) == ["hembra", "macho grande", "categoria"]
