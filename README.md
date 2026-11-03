# Pipeline_Liquidaciones_Ganado · App de depuración y análisis

App web en **Flask (patrón MVC)** para conocer, limpiar, validar, analizar y
comunicar liquidaciones de ganado.

Diseñada para desplegarse en **Render**:

- **Sin base de datos**: todo el estado vive **en memoria** durante la vida del proceso.
- **Sin APIs de IA**: las propuestas de limpieza y los informes se redactan con
  reglas escritas en Python (deterministas) y se verifican contra los datos reales.
- **Datos empaquetados**: los CSV derivados del PDF y los PDF originales viajan en
  `datos/`, por lo que la app funciona en un sistema de archivos efímero.

## Estructura

```
app_depuracion/
├── app/
│   ├── controllers/main.py     # rutas (delgadas)
│   ├── models/datos.py         # carga de las tablas empaquetadas
│   ├── services/               # perfil, limpieza, validación, análisis, informes
│   ├── templates/              # Jinja (CSS dentro de base.html)
│   └── static/dashboard.js
├── datos/                      # CSV y PDF de origen (solo lectura)
│   ├── liquidacion_animales.csv
│   ├── liquidacion_resumen.csv
│   └── insumos/*.pdf
├── tests/                      # pytest (no llaman a la red)
├── requirements.txt            # dependencias para Render
├── render.yaml                 # blueprint de Render
├── Procfile
└── wsgi.py                     # punto de entrada (app = create_app())
```

## Ejecutar en local

```bash
cd app_depuracion
uv run python -m flask --app wsgi run --port 5000
# o doble clic en iniciar_app.bat
```

Abra http://127.0.0.1:5000

## Desplegar en Render

1. Suba este repositorio a GitHub.
2. En Render: **New → Blueprint** y seleccione el repositorio (usa `render.yaml`).
3. Listo: Render instala `requirements.txt` y arranca con
   `gunicorn wsgi:app --bind 0.0.0.0:$PORT`.

> `gunicorn` no corre en Windows; para producción en Render sí. En local use Flask.

## Flujo de la app

`Inicio` → «Ejecutar limpieza y validación» → `/validar` → `/informe_calidad`
→ `/dashboard` → `/informe` → aprobar (el informe aprobado se puede descargar).

## Pruebas

```bash
uv run pytest
```
