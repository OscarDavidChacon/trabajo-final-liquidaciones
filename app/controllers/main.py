"""Controlador principal (delgado, sin lógica de negocio).

Todo el estado vive en memoria (``current_app.extensions``): no se escribe ni
se lee nada del disco en tiempo de ejecución. Los archivos descargables se
generan al vuelo desde los objetos guardados en memoria.
"""

import datetime
import io
import json

import pandas as pd
from flask import (Blueprint, current_app, flash, jsonify, redirect,
                   render_template, request, send_file, url_for)

from ..models.datos import cargar_tablas
from ..services.agente_calidad import (proponer_reglas, redactar_informe,
                                       resaltar, verificar_cifras, verificar_propuestas)
from ..services.agente_informe import generar as generar_informe
from ..services.agente_informe import renderizar_markdown
from ..services.analisis import analisis_completo
from ..services.limpieza import limpiar
from ..services.perfil import hallazgos, inventario, perfil_tabla, resumen_ejecutivo
from ..services.validacion import validar

bp = Blueprint("main", __name__)


def _tablas():
    """Carga las tablas fuente (empaquetadas) una sola vez y las guarda en memoria."""
    tablas = current_app.extensions.get("tablas")
    if tablas is None:
        tablas = cargar_tablas(current_app.config["RUTA_DATOS"])
        current_app.extensions["tablas"] = tablas
    return tablas


def _csv_bytes(df):
    """Serializa un DataFrame a CSV con BOM (Excel-friendly) en memoria."""
    return df.to_csv(index=False, encoding="utf-8-sig").encode("utf-8-sig")


@bp.get("/")
def inicio():
    """Página de inicio: estado de Insumos y botón de limpieza/validación."""
    from pathlib import Path
    ruta_insumos = Path(current_app.config["RUTA_INSUMOS"])
    if ruta_insumos.is_dir():
        archivos = sorted(p.name for p in ruta_insumos.iterdir() if p.is_file())
    else:
        archivos = []
    return render_template(
        "inicio.html",
        archivos=archivos,
        ruta_insumos=str(ruta_insumos),
        limpieza_lista=current_app.extensions.get("validacion") is not None,
    )


@bp.get("/conocer")
def conocer():
    """Entrega A: inventario, hallazgos y perfil por tabla."""
    try:
        tablas = _tablas()
    except FileNotFoundError as error:
        return render_template("conocer.html", error=str(error)), 200

    perfiles = {nombre: perfil_tabla(df) for nombre, df in tablas.items()}
    return render_template(
        "conocer.html",
        inventario=inventario(tablas),
        hallazgos=hallazgos(tablas),
        perfiles=perfiles,
        resumen=resumen_ejecutivo(tablas),
    )


@bp.post("/ejecutar")
def ejecutar():
    """Entregas B y C: limpiar -> validar (todo en memoria) -> /validar."""
    tablas = _tablas()
    resultado = limpiar(tablas)
    revision = validar(tablas, resultado)

    current_app.extensions["limpieza"] = resultado
    current_app.extensions["validacion"] = revision
    current_app.extensions.pop("analisis", None)
    current_app.extensions.pop("informe_calidad", None)
    current_app.extensions.pop("informe_gerencial", None)
    return redirect(url_for("main.validar_vista"))


@bp.get("/limpiar")
def limpiar_vista():
    """Entrega B: muestra la bitácora de la limpieza."""
    resultado = current_app.extensions.get("limpieza")
    if not resultado:
        return render_template("limpiar.html", bitacora=None)
    base = resultado["base"]
    return render_template(
        "limpiar.html",
        bitacora=resultado["bitacora"],
        eliminados=resultado["eliminados"],
        base_filas=len(base),
        base_columnas=len(base.columns),
    )


@bp.get("/validar")
def validar_vista():
    """Entrega C: veredicto, cifras de control, pruebas y descargas."""
    return render_template("validar.html", validacion=current_app.extensions.get("validacion"))


@bp.get("/descargar/<archivo>")
def descargar(archivo):
    """Descarga los archivos generados, construidos en memoria."""
    ext = current_app.extensions
    limpieza = ext.get("limpieza")
    revision = ext.get("validacion")

    if archivo == "base_limpia.csv" and limpieza:
        data, mimetype = _csv_bytes(limpieza["base"]), "text/csv"
    elif archivo == "bitacora_limpieza.csv" and limpieza:
        data, mimetype = _csv_bytes(pd.DataFrame(limpieza["bitacora"])), "text/csv"
    elif archivo == "cifras_control.csv" and revision:
        data, mimetype = _csv_bytes(pd.DataFrame(revision["tabla"])), "text/csv"
    elif archivo == "informe_gerencial.md" and ext.get("informe_gerencial_aprobado"):
        data, mimetype = ext["informe_gerencial_aprobado"].encode("utf-8"), "text/markdown"
    else:
        flash("No hay datos generados para ese archivo. Ejecute la limpieza y validación.", "error")
        return redirect(url_for("main.inicio"))
    return send_file(io.BytesIO(data), mimetype=mimetype, as_attachment=True, download_name=archivo)


@bp.post("/informe_calidad")
def informe_calidad_generar():
    """Entrega D: propuesta determinista y verificación en Python (sin IA)."""
    revision = current_app.extensions.get("validacion")
    resultado = current_app.extensions.get("limpieza")
    if not revision or not resultado:
        flash("Primero ejecute la limpieza y validación.", "error")
        return redirect(url_for("main.inicio"))
    try:
        tabla_hallazgos = hallazgos(_tablas())
        propuesta = proponer_reglas(tabla_hallazgos)
        verificacion = verificar_propuestas(propuesta, tabla_hallazgos, resultado["bitacora"])
        informe = redactar_informe(revision["antes"], resultado["bitacora"], revision["veredicto"])
        cifras = verificar_cifras(informe, revision["antes"], resultado["bitacora"])
        current_app.extensions["informe_calidad"] = {
            "propuesta": propuesta, "verificacion": verificacion,
            "informe": informe, "cifras": cifras,
        }
    except Exception as error:  # errores inesperados de datos
        current_app.extensions["informe_calidad"] = {"error": str(error)}
    return redirect(url_for("main.informe_calidad_vista"))


@bp.get("/informe_calidad")
def informe_calidad_vista():
    """Entrega D: propuestas, alertas, informe y decisión."""
    if not current_app.extensions.get("validacion"):
        flash("Primero ejecute la limpieza y validación.", "error")
        return redirect(url_for("main.inicio"))
    datos = current_app.extensions.get("informe_calidad")
    contexto = {"datos": datos}
    if datos and "informe" in datos:
        tokens = {x["numero"] for x in datos["cifras"]["no_verificadas"]}
        campos = datos["informe"] if isinstance(datos["informe"], dict) else datos["informe"].model_dump()
        propuesta = datos["propuesta"] if isinstance(datos["propuesta"], dict) else datos["propuesta"].model_dump()
        contexto["verificacion"] = datos["verificacion"]
        contexto["alertas"] = propuesta.get("alertas_seguridad", [])
        contexto["cifras"] = datos["cifras"]
        contexto["informe_html"] = {
            "resumen_ejecutivo": resaltar(campos.get("resumen_ejecutivo", ""), tokens),
            "riesgos": [resaltar(t, tokens) for t in campos.get("riesgos_para_el_analisis", [])],
            "recomendaciones": [resaltar(t, tokens) for t in campos.get("recomendaciones", [])],
        }
    contexto["decision"] = current_app.extensions.get("decision")
    return render_template("informe_calidad.html", **contexto)


def _analisis():
    """Calcula el análisis una sola vez desde la limpieza en memoria."""
    analisis = current_app.extensions.get("analisis")
    if analisis is None:
        resultado = current_app.extensions.get("limpieza")
        if not resultado:
            raise FileNotFoundError(
                "Todavía no hay datos limpios. En Inicio pulse «Ejecutar limpieza y validación»."
            )
        tablas = _tablas()
        analisis = analisis_completo(resultado["base"], tablas["resumen"])
        current_app.extensions["analisis"] = analisis
    return analisis


@bp.get("/dashboard")
def dashboard():
    """Entrega F: 4 KPIs y gráficos (Plotly)."""
    try:
        analisis = _analisis()
    except FileNotFoundError as error:
        flash(str(error), "error")
        return redirect(url_for("main.inicio"))
    return render_template("dashboard.html", a=analisis)


@bp.get("/dashboard/datos")
def dashboard_datos():
    """Entrega F: entrega el análisis como JSON para dashboard.js."""
    try:
        return jsonify(_analisis())
    except FileNotFoundError as error:
        return jsonify({"error": str(error)}), 409


@bp.post("/decision")
def decision():
    """Guarda la decisión humana (en memoria) con comentario obligatorio."""
    eleccion = request.form.get("decision", "")
    comentario = (request.form.get("comentario") or "").strip()
    if eleccion not in ("Aprobar base", "Rechazar base") or not comentario:
        flash("Debe elegir Aprobar/Rechazar y escribir un comentario obligatorio.", "error")
        return redirect(url_for("main.informe_calidad_vista"))
    registro = {
        "fecha": datetime.datetime.now().isoformat(timespec="seconds"),
        "decision": eleccion,
        "comentario": comentario,
    }
    current_app.extensions["decision"] = registro
    flash(f"Decisión guardada: {eleccion}. (Se mantiene en memoria del servidor.)", "info")
    return redirect(url_for("main.informe_calidad_vista"))


@bp.get("/informe")
def informe_vista():
    """Entrega G: informe gerencial (determinista, sin IA)."""
    if not current_app.extensions.get("analisis"):
        flash("Primero abra el Dashboard para calcular el análisis.", "error")
        return redirect(url_for("main.dashboard"))
    datos = current_app.extensions.get("informe_gerencial")
    contexto = {"datos": datos, "aprobado": current_app.extensions.get("informe_gerencial_aprobado")}
    if datos and "informe" in datos:
        contexto["informe_html"] = renderizar_markdown(datos["informe"])
        contexto["verificadas"] = datos["verificadas"]
        contexto["no_verificadas"] = datos["no_verificadas"]
    return render_template("informe.html", **contexto)


@bp.post("/informe/generar")
def informe_generar():
    """Entrega G: se redacta con plantillas y Python verifica cada cifra."""
    analisis = current_app.extensions.get("analisis")
    if not analisis:
        flash("Primero abra el Dashboard para calcular el análisis.", "error")
        return redirect(url_for("main.dashboard"))
    try:
        current_app.extensions["informe_gerencial"] = generar_informe(analisis)
    except Exception as error:
        current_app.extensions["informe_gerencial"] = {"error": str(error)}
    return redirect(url_for("main.informe_vista"))


@bp.post("/informe/decision")
def informe_decision():
    """Aprobar/rechazar el informe (en memoria) con comentario obligatorio."""
    datos = current_app.extensions.get("informe_gerencial") or {}
    accion = request.form.get("accion")
    comentario = (request.form.get("comentario") or "").strip()
    informe_editado = request.form.get("informe") or datos.get("informe", "")
    autor = (request.form.get("autor") or "Responsable de liquidaciones (supuesto)").strip()
    if accion not in ("aprobar", "rechazar") or not comentario:
        flash("Debe elegir Aprobar/Rechazar y escribir un comentario obligatorio.", "error")
        return redirect(url_for("main.informe_vista"))
    fecha = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    if accion == "aprobar":
        contenido = (f"# Informe gerencial\n\n- Fecha: {fecha}\n- Autor: {autor}\n"
                     f"- Comentario: {comentario}\n\n---\n\n{informe_editado}\n")
        current_app.extensions["informe_gerencial_aprobado"] = contenido
        current_app.extensions.pop("informe_rechazado", None)
        flash("Informe aprobado. Puede descargarlo; se mantiene en memoria del servidor.", "info")
    else:
        current_app.extensions["informe_rechazado"] = {
            "fecha": fecha, "autor": autor, "comentario": comentario,
        }
        current_app.extensions.pop("informe_gerencial_aprobado", None)
        flash("Informe rechazado. El comentario se mantiene en memoria del servidor.", "info")
    return redirect(url_for("main.informe_vista"))
