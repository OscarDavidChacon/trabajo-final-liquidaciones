"""Limpieza con las reglas R sobre COPIAS, con bitácora.

Reglas (de .agent/rules/proyecto.md):
  R1 Corregir  fecha dd/mm/aaaa -> ISO
  R2 Corregir  numéricos con separadores -> número
  R3 Eliminar  duplicado exacto por liquidacion_id + Número
  R4 Marcar    pesos no positivos / Peso Canal > Peso Pie / rendimiento fuera de 0-100
  R5 Marcar    Arete vacío, Número repetido, Canal no confirmado
  R6 Marcar    discrepancias de conciliación
Nunca rellena vacíos con promedios.
"""

import pandas as pd

from .perfil import a_numero

COLS_NUM_DET = ["Peso Pie", "Peso Canal", "Rendi %", "Precio col.", "Bono", "Precio KG", "Total colones"]
COLS_NUM_RES = ["total_materia_prima", "total_bonos", "total_ingresos", "iva", "subtotal",
                "total_deducciones", "total_neto_a_pagar", "detalle_peso_pie", "detalle_peso_canal",
                "detalle_total_colones"]
LLAVE = ["liquidacion_id", "Número"]


def normalizar_texto(serie):
    """Minúsculas, sin tildes, sin espacios dobles (reutilizable)."""
    s = serie.astype("string").str.strip().str.lower()
    s = s.str.normalize("NFKD").str.encode("ascii", "ignore").str.decode("ascii")
    return s.str.replace(r"\s+", " ", regex=True)


def limpiar(tablas):
    """Devuelve {base, eliminados, bitacora} trabajando sobre copias."""
    animales = tablas["animales"].copy().reset_index(drop=True)
    resumen = tablas["resumen"].copy().reset_index(drop=True)
    bitacora, eliminados = [], []
    marcas = [[] for _ in range(len(animales))]

    def registrar(regla, accion, tabla, descripcion, filas):
        bitacora.append({"regla": regla, "accion": accion, "tabla": tabla,
                         "descripcion": descripcion, "filas_afectadas": int(filas)})

    # ---- R1 Corregir: fecha dd/mm/aaaa -> ISO (conservando el original) ----
    filas_r1 = 0
    for col in ["fecha", "fecha_matanza"]:
        if col in resumen.columns:
            resumen[col + "_original"] = resumen[col]
            convertida = pd.to_datetime(resumen[col], format="%d/%m/%Y", errors="coerce")
            filas_r1 += int(convertida.notna().sum())
            resumen[col] = convertida.dt.strftime("%Y-%m-%d")
    registrar("R1", "Corregir", "resumen",
              "Fecha y fecha de matanza dd/mm/aaaa convertidas a ISO (original en *_original)", len(resumen))

    # ---- R2 Corregir: numéricos tipo texto -> número ----
    tenia_num = animales[COLS_NUM_DET].apply(
        lambda s: s.astype("string").str.strip().ne("") & s.astype("string").str.strip().notna()
    ).any(axis=1)
    filas_r2 = int(tenia_num.sum())
    for col in COLS_NUM_DET:
        animales[col] = a_numero(animales[col])
    for col in COLS_NUM_RES:
        if col in resumen.columns:
            resumen[col] = a_numero(resumen[col])
    registrar("R2", "Corregir", "animales",
              f"{len(COLS_NUM_DET)} columnas numéricas de texto a número "
              f"({filas_r2 * len(COLS_NUM_DET)} celdas); también los montos del resumen", filas_r2)

    # ---- R3 Eliminar: duplicado exacto por liquidacion_id + Número ----
    exactos = animales.duplicated(keep="first")
    idx_eliminar = list(animales.index[exactos])
    for _, fila in animales.loc[idx_eliminar, LLAVE].iterrows():
        eliminados.append({"liquidacion_id": fila["liquidacion_id"], "Número": fila["Número"]})
    if idx_eliminar:
        marcas = [m for i, m in enumerate(marcas) if i not in set(idx_eliminar)]
        animales = animales.drop(index=idx_eliminar).reset_index(drop=True)
    # conflictos: misma llave con valores distintos -> no eliminar, marcar
    conflicto = animales.duplicated(subset=LLAVE, keep=False)
    registrar("R3", "Eliminar", "animales",
              "Duplicado exacto por liquidacion_id + Número eliminado; "
              "si hay conflicto de valores se marca y no se elimina", len(idx_eliminar))

    # ---- R4 Marcar: pesos / rendimiento ----
    n = len(animales)
    m4 = ((animales["Peso Pie"] <= 0) | (animales["Peso Canal"] <= 0)
          | (animales["Peso Canal"] > animales["Peso Pie"])
          | (animales["Rendi %"] < 0) | (animales["Rendi %"] > 100)).fillna(False)
    marcas = [[] for _ in range(n)]
    for i in range(n):
        if bool(m4.iloc[i]):
            marcas[i].append("R4:peso")
    registrar("R4", "Marcar", "animales",
              "Pesos no positivos, Peso Canal > Peso Pie o rendimiento fuera de 0-100", int(m4.sum()))

    # ---- R5 Marcar: Arete vacío, Número repetido, Canal no confirmado ----
    arete_vacio = animales["Arete"].astype("string").str.strip().eq("").fillna(False)
    numero_rep = animales.duplicated(subset=LLAVE, keep=False)
    canal_incierto = pd.Series(True, index=animales.index)  # el PDF no trae valores de Canal
    for i in range(n):
        if bool(arete_vacio.iloc[i]):
            marcas[i].append("R5:arete")
        if bool(numero_rep.iloc[i]):
            marcas[i].append("R5:numero")
        if bool(canal_incierto.iloc[i]):
            marcas[i].append("R5:canal")
    filas_r5 = int((arete_vacio | numero_rep | canal_incierto).sum())
    registrar("R5", "Marcar", "animales",
              f"Arete vacío={int(arete_vacio.sum())}, Número repetido={int(numero_rep.sum())}, "
              f"Canal sin valores/sin confirmar={int(canal_incierto.sum())}", filas_r5)

    # ---- R6 Marcar: conciliación detalle vs cabecera ----
    liq_en_discrepancia = set()
    for _, r in resumen.iterrows():
        det = animales[animales["liquidacion_id"] == r["liquidacion_id"]]
        suma_det = float(det["Total colones"].sum())
        ingresos = float(r["total_ingresos"]) if pd.notna(r["total_ingresos"]) else 0.0
        neto = float(r["total_neto_a_pagar"]) if pd.notna(r["total_neto_a_pagar"]) else 0.0
        iva = float(r["iva"]) if pd.notna(r["iva"]) else 0.0
        ded = float(r["total_deducciones"]) if pd.notna(r["total_deducciones"]) else 0.0
        descuadra = (abs(suma_det - ingresos) > 0.5) or (abs((ingresos + iva - ded) - neto) > 0.5)
        if descuadra:
            liq_en_discrepancia.add(r["liquidacion_id"])
    m6 = animales["liquidacion_id"].isin(liq_en_discrepancia)
    for i in range(n):
        if bool(m6.iloc[i]):
            marcas[i].append("R6:conciliacion")
    registrar("R6", "Marcar", "animales",
              "Discrepancias entre suma del detalle, ingresos, bonos, deducciones, IVA y neto",
              int(m6.sum()))

    # ---- base: una fila por liquidacion_id + Número con las marcas ----
    base = animales.copy()
    base["marcas"] = [";".join(m) for m in marcas]
    if conflicto.any():
        base["marcas"] = base["marcas"].where(base["marcas"].ne(""), "R3:conflicto")

    return {"base": base, "eliminados": eliminados, "bitacora": bitacora}
