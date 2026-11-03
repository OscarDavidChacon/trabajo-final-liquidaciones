"""Cifras de control y veredicto. Todo se recalcula desde las tablas originales.

No confía en los números que trae limpieza.py: vuelve a sumar y contar.
"""

import pandas as pd

from .perfil import a_numero

LLAVE = ["liquidacion_id", "Número"]


def cifras_control(tablas):
    """Filas, llaves únicas y sumas de control (ficha D)."""
    animales = tablas["animales"]
    resumen = tablas["resumen"]
    return {
        "filas": int(len(animales)),
        "llaves_unicas": int(animales.drop_duplicates(subset=LLAVE).shape[0]),
        "suma_total_colones": float(a_numero(animales["Total colones"]).sum()),
        "suma_peso_pie": float(a_numero(animales["Peso Pie"]).sum()),
        "suma_peso_canal": float(a_numero(animales["Peso Canal"]).sum()),
        "total_neto_a_pagar": float(a_numero(resumen["total_neto_a_pagar"]).sum()),
        "total_ingresos": float(a_numero(resumen["total_ingresos"]).sum()),
        "total_bonos": float(a_numero(resumen["total_bonos"]).sum()),
        "total_deducciones": float(a_numero(resumen["total_deducciones"]).sum()),
    }


def _suma_eliminadas(animales_originales, eliminados):
    """Suma de Total colones de las filas que la limpieza eliminó (una entrada = una fila)."""
    total = 0.0
    for llave in eliminados:
        coincide = animales_originales[
            (animales_originales["liquidacion_id"] == llave["liquidacion_id"])
            & (animales_originales["Número"] == llave["Número"])
        ]
        if len(coincide):
            total += float(a_numero(coincide["Total colones"]).iloc[0])
    return total


def validar(tablas, limpio):
    """Devuelve tabla ANTES/DESPUÉS/DIFERENCIA/EXPLICACIÓN, pruebas y veredicto."""
    base = limpio["base"]
    eliminados = limpio["eliminados"]

    antes = cifras_control(tablas)
    despues = cifras_control({"animales": base, "resumen": tablas["resumen"]})
    suma_elim = _suma_eliminadas(tablas["animales"], eliminados)
    n_elim = len(eliminados)

    tabla = [
        {"metrica": "Filas de detalle", "antes": antes["filas"], "despues": despues["filas"],
         "diferencia": despues["filas"] - antes["filas"],
         "explicacion": f"R3: {n_elim} duplicado(s) exacto(s) eliminado(s)"},
        {"metrica": "Llaves únicas (liquidacion_id + Número)",
         "antes": antes["llaves_unicas"], "despues": despues["llaves_unicas"],
         "diferencia": despues["llaves_unicas"] - antes["llaves_unicas"],
         "explicacion": "R3: sin llaves duplicadas"},
        {"metrica": "Suma Total colones",
         "antes": round(antes["suma_total_colones"], 2), "despues": round(despues["suma_total_colones"], 2),
         "diferencia": round(despues["suma_total_colones"] - antes["suma_total_colones"], 2),
         "explicacion": "R2 solo convierte texto a número; R3 descuenta las filas eliminadas"},
        {"metrica": "Suma Peso Pie",
         "antes": round(antes["suma_peso_pie"], 2), "despues": round(despues["suma_peso_pie"], 2),
         "diferencia": round(despues["suma_peso_pie"] - antes["suma_peso_pie"], 2),
         "explicacion": "R2 solo convierte texto a número (no cambia el valor)"},
        {"metrica": "Suma Peso Canal",
         "antes": round(antes["suma_peso_canal"], 2), "despues": round(despues["suma_peso_canal"], 2),
         "diferencia": round(despues["suma_peso_canal"] - antes["suma_peso_canal"], 2),
         "explicacion": "R2 solo convierte texto a número (no cambia el valor)"},
        {"metrica": "TOTAL NETO A PAGAR (cabecera)",
         "antes": round(antes["total_neto_a_pagar"], 2), "despues": round(despues["total_neto_a_pagar"], 2),
         "diferencia": round(despues["total_neto_a_pagar"] - antes["total_neto_a_pagar"], 2),
         "explicacion": "R1 solo cambia el formato de la fecha; no altera montos"},
    ]

    resumen = tablas["resumen"]
    conciliacion_ok = True
    for _, r in resumen.iterrows():
        neto = float(a_numero(pd.Series([r["total_neto_a_pagar"]])).iloc[0])
        ing = float(a_numero(pd.Series([r["total_ingresos"]])).iloc[0])
        iva = float(a_numero(pd.Series([r["iva"]])).iloc[0])
        ded = float(a_numero(pd.Series([r["total_deducciones"]])).iloc[0])
        if abs((ing + iva - ded) - neto) > 0.5:
            conciliacion_ok = False
    fechas_validas = bool(pd.to_datetime(resumen["fecha"], format="%d/%m/%Y", errors="coerce").notna().all())

    pruebas = [
        {"prueba": "filas antes − eliminadas = después", "ok": antes["filas"] - n_elim == despues["filas"]},
        {"prueba": "liquidacion_id + Número única en la base",
         "ok": not base.duplicated(subset=LLAVE).any()},
        {"prueba": "suma Total colones antes − eliminadas = después",
         "ok": abs(antes["suma_total_colones"] - suma_elim - despues["suma_total_colones"]) <= 0.5},
        {"prueba": "cada liquidación de la base existe en el resumen",
         "ok": bool(base["liquidacion_id"].isin(resumen["liquidacion_id"]).all())},
        {"prueba": "neto = ingresos + IVA − deducciones en cada liquidación", "ok": conciliacion_ok},
        {"prueba": "fechas de liquidación válidas", "ok": fechas_validas},
    ]
    veredicto = "APROBADO" if all(p["ok"] for p in pruebas) else "RECHAZADO"

    return {"tabla": tabla, "pruebas": pruebas, "veredicto": veredicto,
            "antes": antes, "despues": despues, "eliminados_suma": round(suma_elim, 2)}
