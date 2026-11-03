"""Análisis (P1, P2, P3) sobre las tablas limpias que viven en memoria.

Reglas D de la memoria:
  D1 universo: solo animales de liquidaciones identificadas, llave única, sin subtotales.
  D2 métricas de tiempo: solo con fechas válidas; serie mensual exige >= 2 meses.
  D3 KPI principal = suma de Total colones (aditivo); el neto de cabecera nunca se suma por animal.
  D4 todo KPI sesgado va con mediana y cuartiles.
  D5 control: límite superior = media + 2 desviaciones estándar.
  D6 gráficos: pastel <= 5 porciones; barras ordenadas; Pareto con acumulado.
No construye pantallas ni HTML: devuelve diccionarios listos para graficar.

El análisis recibe DataFrames ya cargados (no lee del disco). Por compatibilidad
con las pruebas se mantienen ``cargar_base`` y ``cargar_resumen``, que sí leen CSV.
"""

from pathlib import Path

import numpy as np
import pandas as pd

LLAVE = ["liquidacion_id", "Número"]

COLS_NUM_DETALLE = ["Peso Pie", "Peso Canal", "Rendi %", "Precio col.", "Bono", "Precio KG", "Total colones"]
COLS_NUM_RESUMEN = ["total_materia_prima", "total_bonos", "total_ingresos", "iva", "subtotal",
                    "total_deducciones", "total_neto_a_pagar", "detalle_peso_pie", "detalle_peso_canal",
                    "detalle_total_colones"]


def _a_numero(serie):
    return pd.to_numeric(serie.astype("string").str.replace(",", "", regex=False), errors="coerce")


def base_desde_tablas(base, resumen):
    """Aplica D1 sobre la base limpia que ya está en memoria."""
    base = base.copy()
    for col in COLS_NUM_DETALLE:
        if col in base.columns:
            base[col] = _a_numero(base[col])
    base = base.dropna(subset=LLAVE)
    base = base[base["liquidacion_id"].isin(resumen["liquidacion_id"])]   # liquidaciones identificadas
    base = base.drop_duplicates(subset=LLAVE)                              # llave compuesta única
    return base.reset_index(drop=True)


def preparar_resumen(resumen):
    """Agrega la columna ``mes`` (YYYY-MM) a un resumen ya cargado en memoria."""
    resumen = resumen.copy()
    for col in COLS_NUM_RESUMEN:
        if col in resumen.columns:
            resumen[col] = _a_numero(resumen[col])
    fecha = pd.to_datetime(resumen["fecha"], format="%d/%m/%Y", errors="coerce")
    resumen["mes"] = fecha.dt.strftime("%Y-%m")
    return resumen.reset_index(drop=True)


def cargar_base(ruta_resultados):
    """Lee Resultados/base_limpia.csv y aplica D1 (solo para pruebas/locales)."""
    ruta = Path(ruta_resultados) / "base_limpia.csv"
    if not ruta.is_file():
        raise FileNotFoundError(
            "No existe Resultados/base_limpia.csv. Ejecute primero la limpieza "
            "y validación (Inicio → «Ejecutar limpieza y validación»)."
        )
    base = pd.read_csv(ruta, dtype={"liquidacion_id": "string", "Número": "string", "Arete": "string"})
    return base_desde_tablas(base, cargar_resumen(Path(ruta_resultados)))


def cargar_resumen(ruta_resultados):
    """Lee liquidacion_resumen.csv y agrega la columna mes (YYYY-MM)."""
    ruta = Path(ruta_resultados) / "liquidacion_resumen.csv"
    if not ruta.is_file():
        raise FileNotFoundError(f"No existe {ruta}.")
    resumen = pd.read_csv(ruta, dtype={"liquidacion_id": "string", "fecha": "string"})
    return preparar_resumen(resumen)


def _mes_por_liquidacion(resumen):
    return dict(zip(resumen["liquidacion_id"], resumen["mes"]))


def kpis(base):
    """KPIs del universo (D3, D4)."""
    tc = pd.to_numeric(base["Total colones"], errors="coerce")
    marcas = base["marcas"].astype("string").fillna("").str.strip()
    marcadas = marcas.ne("")
    return {
        "filas_universo": int(len(base)),
        "suma_total_colones": round(float(tc.sum()), 2),
        "promedio_total_colones": round(float(tc.mean()), 2),
        "mediana_total_colones": round(float(tc.median()), 2),
        "liquidaciones_unicas": int(base["liquidacion_id"].nunique()),
        "pct_filas_marcadas": round(float(100 * marcadas.mean()), 2),
        "rendimiento_ponderado_pct": round(
            float(100 * pd.to_numeric(base["Peso Canal"], errors="coerce").sum()
                  / pd.to_numeric(base["Peso Pie"], errors="coerce").sum()), 2),
    }


def p1(base, resumen):
    """P1: conciliación de importes de cabecera vs suma del detalle (sin duplicar el neto)."""
    por_liquidacion = []
    mapa_mes = _mes_por_liquidacion(resumen)
    for _, r in resumen.iterrows():
        det = pd.to_numeric(
            base.loc[base["liquidacion_id"] == r["liquidacion_id"], "Total colones"], errors="coerce")
        suma_det = round(float(det.sum()), 2)
        def num(v):
            if pd.isna(v):
                return None
            return round(float(str(v).replace(",", "")) if isinstance(v, str) else float(v), 2)
        ingresos, iva, ded = num(r["total_ingresos"]), num(r["iva"]), num(r["total_deducciones"])
        neto = num(r["total_neto_a_pagar"])
        por_liquidacion.append({
            "liquidacion_id": r["liquidacion_id"],
            "mes": mapa_mes.get(r["liquidacion_id"], ""),
            "total_materia_prima": num(r["total_materia_prima"]),
            "total_bonos": num(r["total_bonos"]),
            "total_ingresos": ingresos,
            "iva": iva,
            "subtotal": num(r["subtotal"]),
            "total_deducciones": ded,
            "total_neto_a_pagar": neto,
            "suma_detalle_total_colones": suma_det,
            "diferencia_detalle_vs_ingresos": round(suma_det - ingresos, 2),
            "identidades_ok": bool(abs((ingresos + iva - ded) - neto) <= 0.5),
        })
    totales = {
        "ingresos": round(sum(x["total_ingresos"] for x in por_liquidacion), 2),
        "neto_a_pagar": round(sum(x["total_neto_a_pagar"] for x in por_liquidacion), 2),
        "suma_detalle_total_colones": round(sum(x["suma_detalle_total_colones"] for x in por_liquidacion), 2),
    }
    return {"por_liquidacion": por_liquidacion, "totales": totales}


def p2(base):
    """P2: valor por animal (Pareto) y pesos/rendimiento/clasificación."""
    tc = pd.to_numeric(base["Total colones"], errors="coerce")
    agrupado = base.assign(_total=tc).groupby("Número", as_index=False)["_total"].sum()
    agrupado = agrupado.sort_values("_total", ascending=False).reset_index(drop=True)
    total = float(agrupado["_total"].sum())
    pct = 100 * agrupado["_total"] / total
    agrupado["pct"] = pct.round(2)
    agrupado["pct_acumulado"] = pct.cumsum().round(2)
    top = agrupado.to_dict(orient="records")
    peso_pie = float(pd.to_numeric(base["Peso Pie"], errors="coerce").sum())
    peso_canal = float(pd.to_numeric(base["Peso Canal"], errors="coerce").sum())
    return {
        "total_colones": round(total, 2),
        "n_animales": int(len(agrupado)),
        "top_por_valor": top,
        "peso_pie_total": round(peso_pie, 2),
        "peso_canal_total": round(peso_canal, 2),
        "rendimiento_ponderado_pct": round(100 * peso_canal / peso_pie, 2) if peso_pie else None,
        "peso_pie_promedio": round(float(pd.to_numeric(base["Peso Pie"], errors="coerce").mean()), 2),
        "rendi_promedio_pct": round(float(pd.to_numeric(base["Rendi %"], errors="coerce").mean()), 2),
        "por_clasificacion": {k: int(v) for k, v in base["Calif."].value_counts().items()},
        "precio_promedio_kg": round(float(pd.to_numeric(base["Precio KG"], errors="coerce").mean()), 2),
    }


def p3(base, resumen):
    """P3: serie mensual de neto, rendimiento y precio (si hay >= 2 meses)."""
    meses = sorted({m for m in resumen["mes"].dropna().unique()})
    if len(meses) < 2:
        return {"disponible": False,
                "motivo": "Se requieren al menos dos liquidaciones de meses distintos.",
                "meses": meses}
    mapa_mes = _mes_por_liquidacion(resumen)
    b = base.assign(mes=base["liquidacion_id"].map(mapa_mes))
    serie = []
    for mes, grupo in b.groupby("mes"):
        pie = float(pd.to_numeric(grupo["Peso Pie"], errors="coerce").sum())
        canal = float(pd.to_numeric(grupo["Peso Canal"], errors="coerce").sum())
        serie.append({
            "mes": mes,
            "suma_total_colones": round(float(pd.to_numeric(grupo["Total colones"], errors="coerce").sum()), 2),
            "rendimiento_pct": round(100 * canal / pie, 2) if pie else None,
            "precio_promedio_kg": round(float(pd.to_numeric(grupo["Precio KG"], errors="coerce").mean()), 2),
        })
    return {"disponible": True, "serie": serie}


def distribuciones(base):
    """Cuartiles de Total colones y bordes/conteos para un histograma de 20 clases."""
    tc = pd.to_numeric(base["Total colones"], errors="coerce").dropna()
    cuartiles = {f"p{q}": round(float(tc.quantile(q / 100)), 2) for q in (25, 50, 75, 90)}
    conteos, bordes = np.histogram(tc, bins=20)
    return {
        "cuartiles": cuartiles,
        "histograma": {"bordes": [round(float(x), 2) for x in bordes],
                       "conteos": [int(x) for x in conteos]},
        "media": round(float(tc.mean()), 2),
        "mediana": round(float(tc.median()), 2),
    }


def control(base, resumen):
    """Gráfico de control mensual de % de filas marcadas (D5)."""
    mapa_mes = _mes_por_liquidacion(resumen)
    b = base.assign(mes=base["liquidacion_id"].map(mapa_mes))
    b["_marcada"] = b["marcas"].astype("string").fillna("").str.strip().ne("")
    serie = b.groupby("mes")["_marcada"].mean().mul(100).round(2)
    if len(serie) < 2:
        return {"disponible": False,
                "motivo": "Se requieren al menos dos meses para el gráfico de control.",
                "proporcion_vigilada": "% de filas marcadas"}
    media = float(serie.mean())
    desv = float(serie.std(ddof=0))
    limite = round(media + 2 * desv, 2)
    fuera = [m for m, v in serie.items() if v > limite]
    return {
        "disponible": True,
        "proporcion_vigilada": "% de filas marcadas",
        "serie": {m: float(v) for m, v in serie.items()},
        "media": round(media, 2),
        "desviacion": round(desv, 2),
        "limite_superior": limite,
        "meses_fuera_de_control": fuera,
    }


def _redondear(obj):
    if isinstance(obj, dict):
        return {k: _redondear(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_redondear(v) for v in obj]
    if isinstance(obj, (np.integer,)):
        return int(obj)
    if isinstance(obj, (np.floating,)):
        return round(float(obj), 2)
    if isinstance(obj, float):
        return round(obj, 2)
    return obj


def analisis_completo(base_o_ruta, resumen=None):
    """Ejecuta todo y devuelve un diccionario serializable a JSON.

    - ``analisis_completo(base_df, resumen_df)`` trabaja con datos en memoria.
    - ``analisis_completo(ruta_resultados)`` (compatibilidad) lee los CSV locales.
    """
    if isinstance(base_o_ruta, (str, Path)):
        ruta = base_o_ruta
        base = cargar_base(ruta)
        resumen = cargar_resumen(ruta)
    else:
        base = base_desde_tablas(base_o_ruta, resumen)
        resumen = preparar_resumen(resumen)
    resultado = {
        "kpis": kpis(base),
        "p1": p1(base, resumen),
        "p2": p2(base),
        "p3": p3(base, resumen),
        "distribuciones": distribuciones(base),
        "control": control(base, resumen),
    }
    return _redondear(resultado)
