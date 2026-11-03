"""Fábrica de la aplicación Flask (patrón MVC).

La aplicación no usa base de datos ni escribe en disco: todo el estado
(tablas cargadas, limpieza, validación, análisis e informes) vive en memoria
durante la vida del proceso. Esto la hace apta para un hosting efímero como
Render, donde el sistema de archivos no persiste.

Los datos de origen (CSV derivados del PDF y los PDF originales) viajan
dentro del propio despliegue en la carpeta ``datos/``:

    app_depuracion/datos/liquidacion_animales.csv
    app_depuracion/datos/liquidacion_resumen.csv
    app_depuracion/datos/insumos/*.pdf   (solo lectura)
"""

import os
from pathlib import Path

from dotenv import load_dotenv
from flask import Flask

# .../app_depuracion
BASE_DIR = Path(__file__).resolve().parent.parent
# datos empaquetados dentro de la app (se despliegan con el repositorio)
RUTA_DATOS = (BASE_DIR / "datos").resolve()
RUTA_INSUMOS = (RUTA_DATOS / "insumos").resolve()


def create_app():
    """Crea y configura la aplicación Flask."""
    load_dotenv(BASE_DIR / ".env")

    app = Flask(__name__)
    app.config["RUTA_DATOS"] = str(RUTA_DATOS)
    app.config["RUTA_INSUMOS"] = str(RUTA_INSUMOS)
    app.secret_key = os.getenv("SECRET_KEY", "pipeline-liquidaciones-ganado")

    @app.template_filter("miles")
    def miles(valor):
        """Formatea números con separador de miles (punto en Costa Rica)."""
        if isinstance(valor, bool) or not isinstance(valor, (int, float)):
            return valor
        texto = f"{valor:,.0f}" if float(valor).is_integer() else f"{valor:,.2f}"
        return texto.replace(",", "\u00a0")

    from .controllers.main import bp as main_bp

    app.register_blueprint(main_bp)

    return app
