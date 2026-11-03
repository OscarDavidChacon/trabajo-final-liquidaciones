"""Carga de las tablas derivadas del PDF (solo lectura de Resultados).

El PDF de Insumos no tiene hojas Excel: la extracción a CSV se hizo una sola
vez (ver la memoria del proyecto) y aquí solo se leen esos CSV.
"""

from pathlib import Path

import pandas as pd

ARCHIVOS = {
    "animales": "liquidacion_animales.csv",
    "resumen": "liquidacion_resumen.csv",
}


def cargar_tablas(ruta):
    """Lee Resultados/liquidacion_animales.csv y liquidacion_resumen.csv.

    Devuelve {'animales': DataFrame, 'resumen': DataFrame}.
    Si falta el archivo, lanza FileNotFoundError con su nombre.
    """
    ruta = Path(ruta)
    tablas = {}
    for nombre, archivo in ARCHIVOS.items():
        destino = ruta / archivo
        if not destino.is_file():
            raise FileNotFoundError(
                f"No se encontró el archivo '{archivo}' en {ruta}. "
                f"Falta la tabla '{nombre}' generada desde el PDF."
            )
        # Se lee como texto para conservar los valores tal como vienen del PDF
        # (con separadores de miles, ceros a la izquierda en Arete, etc.).
        tablas[nombre] = pd.read_csv(destino, dtype="string", keep_default_na=False)
    return tablas
