"""Pruebas de calidad de datos: propuesta determinista y verificación en Python."""

from app.services.agente_calidad import (FAMILIA_A_ACCION, proponer_reglas,
                                         redactar_informe, verificar_cifras,
                                         verificar_propuestas)

HALLAZGOS = [
    {"id": "H01", "familia": "Tipo de dato incorrecto", "tabla": "animales",
     "descripcion": "numéricas como texto", "cantidad": 140, "tipo": "Calidad"},
    {"id": "H02", "familia": "Vacíos", "tabla": "animales",
     "descripcion": "Canal vacío", "cantidad": 20, "tipo": "Calidad"},
]
BITACORA = [
    {"regla": "R1", "accion": "Corregir", "tabla": "resumen", "descripcion": "", "filas_afectadas": 2},
    {"regla": "R2", "accion": "Corregir", "tabla": "animales", "descripcion": "", "filas_afectadas": 20},
    {"regla": "R3", "accion": "Eliminar", "tabla": "animales", "descripcion": "", "filas_afectadas": 0},
    {"regla": "R5", "accion": "Marcar", "tabla": "animales", "descripcion": "", "filas_afectadas": 20},
]


def test_proponer_reglas_coincide_con_el_pipeline():
    propuesta = proponer_reglas(HALLAZGOS)
    assert len(propuesta["reglas"]) == len(HALLAZGOS)
    for regla, hallazgo in zip(propuesta["reglas"], HALLAZGOS):
        assert regla["hallazgo_id"] == hallazgo["id"]
        assert regla["accion"] == FAMILIA_A_ACCION[hallazgo["familia"]]


def test_verificar_propuestas_inexistente_y_coincidencia():
    propuesta = proponer_reglas(HALLAZGOS)
    propuesta["reglas"].append({"hallazgo_id": "H99", "accion": "Marcar",
                                "justificacion": "", "riesgo_si_no_se_trata": ""})
    verificacion = verificar_propuestas(propuesta, HALLAZGOS, BITACORA)
    assert verificacion[0]["estado"] == "existe" and verificacion[0]["coincide"] is True
    assert verificacion[-1]["estado"] == "hallazgo inexistente" and verificacion[-1]["coincide"] is None


def test_verificar_propuestas_difiere():
    propuesta = {"reglas": [{"hallazgo_id": "H01", "accion": "Marcar",
                             "justificacion": "", "riesgo_si_no_se_trata": ""}]}
    verificacion = verificar_propuestas(propuesta, HALLAZGOS, BITACORA)
    # H01 es "Tipo de dato incorrecto" -> el pipeline aplica Corregir, aquí se propuso Marcar
    assert verificacion[0]["coincide"] is False


def test_verificar_cifras_marca_inventada():
    cifras = {"filas": 20, "suma_total_colones": 8292500.0}
    informe = {
        "resumen_ejecutivo": "La suma es 8.292.500,00 colones con 20 filas.",
        "riesgos_para_el_analisis": ["Se detectaron 999 registros problema."],
        "recomendaciones": ["Revisar 20 filas."],
    }
    resultado = verificar_cifras(informe, cifras, BITACORA)
    no_verificadas = {x["numero"] for x in resultado["no_verificadas"]}
    assert "999" in no_verificadas
    assert "8.292.500,00" not in no_verificadas
    assert not any(x["numero"] == "20" for x in resultado["no_verificadas"])


def test_redactar_informe_solo_usa_cifras_verificables():
    cifras = {"filas": 20, "llaves_unicas": 20, "suma_total_colones": 8292500.0,
              "total_neto_a_pagar": 8348187.11, "suma_peso_pie": 6288.5,
              "suma_peso_canal": 3370.5, "total_bonos": 84262.5, "total_deducciones": 27237.96}
    informe = redactar_informe(cifras, BITACORA, "APROBADO")
    revision = verificar_cifras(informe, cifras, BITACORA)
    assert revision["no_verificadas"] == []
