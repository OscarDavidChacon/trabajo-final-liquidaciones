# Guía de despliegue en Render

**Repositorio:** https://github.com/OscarDavidChacon/trabajo-final-liquidaciones
**Repositorio local:** `app_depuracion/` (raíz del repo, con su propio `.git`)
**Rama:** `main`

---

## 1. Resumen de lo que hace la app

App web (Flask, patrón MVC) que **conoce, limpia, valida, analiza y comunica**
liquidaciones de ganado.

Principios del despliegue:

- **Sin base de datos** → todo el estado vive **en memoria** durante la vida del proceso.
- **Sin APIs de IA** → los informes se redactan con reglas escritas en Python
  (deterministas) y se verifican contra los datos reales.
- **Datos empaquetados** → los CSV derivados del PDF y los PDF originales viajan
  dentro del repositorio en `datos/`, por lo que la app funciona en un sistema de
  archivos efímero como el de Render.

---

## 2. Qué se cambió para Render

| Tema | Antes | Ahora |
|---|---|---|
| Persistencia | Escribía CSV/JSON/MD en `Resultados/` | Todo en memoria (`current_app.extensions`) |
| IA | Gemini / OpenRouter | Reglas y plantillas en Python |
| Datos | `../Insumos` y `../Resultados` (fuera del repo) | `datos/` dentro del repo |
| Dependencias | flask, google-genai, openpyxl, pandas, pymupdf, python-dotenv | flask, pandas, numpy, python-dotenv (+ gunicorn en Render) |
| Archivos nuevos | — | `requirements.txt`, `render.yaml`, `Procfile` |

Archivos eliminados: `app/services/openrouter.py`, `app/models/schemas.py`.

---

## 3. Ejecutar en local (Windows)

```bash
cd "app_depuracion"
uv run python -m flask --app wsgi run --port 5000
# o doble clic en iniciar_app.bat
```

Abrir http://127.0.0.1:5000

> En este equipo el Control de aplicaciones de Windows bloquea `flask.exe` y
> `pytest.exe`; por eso se usa `python -m flask` y `python -m pytest`.

### Pruebas

```bash
uv run python -m pytest
```

---

## 4. Desplegar en Render (paso a paso)

1. Entrar a **https://render.com** e iniciar sesión.
2. **New +** → **Blueprint**.
3. Conectar el repositorio `OscarDavidChacon/trabajo-final-liquidaciones`.
4. Render detecta automáticamente `render.yaml`. Confirmar y pulsar **Apply/Deploy**.
5. Esperar el build. Render ejecuta:
   - **Build:** `pip install -r requirements.txt`
   - **Start:** `gunicorn wsgi:app --bind 0.0.0.0:$PORT --workers 1 --threads 4 --timeout 120`
6. Abrir la URL pública del servicio y pulsar **«Ejecutar limpieza y validación»**.

### Configuración que aporta `render.yaml`

- `runtime: python`, `plan: free`
- `PYTHON_VERSION=3.12.10`
- `SECRET_KEY` generada automáticamente (`generateValue: true`)

---

## 5. Notas importantes

- **Plan free:** el servicio se "duerme" por inactividad. Al despertar, el
  **estado en memoria se reinicia**, así que hay que volver a ejecutar la
  limpieza/validación. Es el comportamiento acordado (sin base de datos).
- **Descargas:** `base_limpia.csv`, `bitacora_limpieza.csv`, `cifras_control.csv`
  y `informe_gerencial.md` se generan al vuelo desde la memoria.
- **Secretos:** `.env` está en `.gitignore` y **no** se publica. La app no
  necesita claves de IA.
- **Gunicorn** no corre en Windows; en local usa Flask, en Render usa Gunicorn.

---

## 6. Flujo de la app

```
Inicio → «Ejecutar limpieza y validación» → /validar → /informe_calidad
       → /dashboard → /informe → aprobar (descargable)
```

---

## 7. Solución de problemas

| Síntoma | Causa probable | Solución |
|---|---|---|
| "Ejecutar limpieza..." no muestra datos | Servicio dormido/reiniciado | Volver a ejecutar la limpieza |
| Build falla al instalar pandas/numpy | Versión de Python | Verificar `PYTHON_VERSION=3.12.10` |
| La app responde lento la primera vez | Arranque desde suspensión (plan free) | Es normal, esperar unos segundos |

---

## 8. Historial de commits relevantes

| Commit | Descripción |
|---|---|
| `0039721` | App adaptada a Render: estado en memoria, sin IA, datos empaquetados |
| `315d2e1` | `.env.example` limpio (solo `SECRET_KEY`) |
| (siguiente) | Guía de despliegue |
