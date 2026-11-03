"""Perfil e inventario de las tablas y hallazgos (6 errores típicos + Negocio).

No modifica datos: solo describe lo que ve.
"""

import pandas as pd

COLUMNAS_NUMERICAS_DETALLE = [
    "Peso Pie", "Peso Canal", "Rendi %", "Precio col.", "Bono", "Precio KG", "Total colones",
]


def _serie_texto(serie):
    return serie.astype("string")


def _vacios(serie):
    s = _serie_texto(serie)
    return int((s.isna() | (s.str.strip() == "")).sum())


def a_numero(serie):
    """Convierte texto tipo '2,425.00' a número; lo que no se pueda, NaN."""
    return pd.to_numeric(
        _serie_texto(serie).str.replace(",", "", regex=False).str.strip(),
        errors="coerce",
    )


def perfil_tabla(df):
    """Una fila por columna con: dtype, vacíos, distintos, mín/máx/media y ejemplo."""
    filas = []
    for col in df.columns:
        s = _serie_texto(df[col])
        no_vacio = s.where(~(s.isna() | (s.str.strip() == "")), pd.NA)
        numero = a_numero(df[col])
        es_num = bool(numero.notna().any())
        filas.append({
            "columna": col,
            "dtype": str(df[col].dtype),
            "vacios": _vacios(df[col]),
            "distintos": int(no_vacio.nunique()),
            "min": float(numero.min()) if es_num else None,
            "max": float(numero.max()) if es_num else None,
            "media": float(numero.mean()) if es_num else None,
            "ejemplo": (no_vacio.dropna().iloc[0] if int(no_vacio.nunique()) else ""),
        })
    return filas


def inventario(tablas):
    """Resumen por tabla: filas, columnas y total de celdas vacías."""
    return [
        {
            "tabla": nombre,
            "filas": len(df),
            "columnas": len(df.columns),
            "vacios": sum(_vacios(df[c]) for c in df.columns),
        }
        for nombre, df in tablas.items()
    ]


def hallazgos(tablas):
    """Lista de hallazgos con id, familia, tabla, descripción, cantidad y tipo."""
    animales = tablas.get("animales")
    resumen = tablas.get("resumen")
    lista = []
    contador = {"n": 0}

    def add(familia, tabla, descripcion, cantidad, tipo="Calidad"):
        contador["n"] += 1
        lista.append({
            "id": f"H{contador['n']:02d}",
            "familia": familia,
            "tabla": tabla,
            "descripcion": descripcion,
            "cantidad": int(cantidad),
            "tipo": tipo,
        })

    if animales is not None:
        cols_texto = [c for c in COLUMNAS_NUMERICAS_DETALLE
                      if pd.api.types.is_string_dtype(animales[c]) and a_numero(animales[c]).notna().any()]
        add("Tipo de dato incorrecto", "animales",
            f"{len(cols_texto)} columnas numéricas almacenadas como texto: {', '.join(cols_texto)}",
            len(animales) * len(cols_texto))
        add("Vacíos", "animales", "Columna Canal sin ningún valor", _vacios(animales["Canal"]))
        add("Vacíos", "animales", "Arete vacío (identificador que puede faltar)", _vacios(animales["Arete"]))
        add("Duplicados", "animales",
            "Filas duplicadas por la llave liquidacion_id + Número",
            int(animales.duplicated(subset=["liquidacion_id", "Número"]).sum()))
        add("Texto inconsistente", "animales",
            "Categorías Sexo y Calif. sin variantes de escritura (mayúsculas/espacios)",
            0)
        num = animales[COLUMNAS_NUMERICAS_DETALLE].apply(a_numero)
        rango = int((((num[["Peso Pie", "Peso Canal"]] <= 0).any(axis=1))
                     | (num["Peso Canal"] > num["Peso Pie"])
                     | (num["Rendi %"] < 0) | (num["Rendi %"] > 100)).sum())
        add("Fuera de rango o incoherente", "animales",
            "Pesos no positivos, Peso Canal mayor que Peso Pie o rendimiento fuera de 0–100",
            rango)
        tc = num["Total colones"]
        q1, q3 = tc.quantile(0.25), tc.quantile(0.75)
        iqr = q3 - q1
        atipicos = int(((tc < q1 - 1.5 * iqr) | (tc > q3 + 1.5 * iqr)).sum())
        add("Fuera de rango o incoherente", "animales",
            "Valores atípicos por IQR en Total colones",
            atipicos)
        top = tc.max()
        mediana = tc.median()
        add("Negocio", "animales",
            f"Concentración de valor: animal de mayor Total colones ({top:,.2f}) frente a la mediana ({mediana:,.2f})",
            int((tc == top).sum()), tipo="Negocio")

    if animales is not None and resumen is not None:
        huerfanas = int((~animales["liquidacion_id"].isin(resumen["liquidacion_id"])).sum())
        add("Integridad entre tablas", "animales/resumen",
            "Filas de animal sin liquidación en el resumen (huérfanas)", huerfanas)
        meses = resumen["fecha"].astype("string").str[3:10].nunique()
        add("Negocio", "resumen",
            f"Liquidaciones disponibles: {len(resumen)} en {meses} mes(es) distintos "
            f"(con menos de dos meses no hay serie mensual)",
            len(resumen), tipo="Negocio")

    return lista


def resumen_ejecutivo(tablas):
    """Conteos rápidos para la tarjeta superior."""
    inv = inventario(tablas)
    total_hallazgos = len(hallazgos(tablas))
    total_calidad = sum(1 for h in hallazgos(tablas) if h["tipo"] == "Calidad")
    return {
        "tablas": len(inv),
        "filas": sum(t["filas"] for t in inv),
        "hallazgos": total_hallazgos,
        "calidad": total_calidad,
    }
