"""Calidad de datos sin IA: propuesta determinista + verificación en Python.

Este módulo reemplaza al antiguo agente de Gemini. Ya no se llama a ninguna API
de IA: las propuestas de limpieza y el informe de calidad se construyen con
reglas escritas en Python a partir de los hallazgos y las cifras de control.
La verificación (``verificar_propuestas`` y ``verificar_cifras``) se mantiene
igual y sigue marcando cualquier cifra que no exista en los datos reales.
"""

import html
import re

# Acción que el pipeline aplica en la memoria para cada familia de hallazgo
# (se usa para comparar "acción propuesta" vs "regla aplicada").
FAMILIA_A_ACCION = {
    "Tipo de dato incorrecto": "Corregir",
    "Vacíos": "Marcar",
    "Duplicados": "Eliminar",
    "Texto inconsistente": "Corregir",
    "Fuera de rango o incoherente": "Marcar",
    "Integridad entre tablas": "Marcar",
    "Negocio": "Marcar",
}

_JUSTIFICACION = {
    "Tipo de dato incorrecto": "El valor es recuperable con certeza al reinterpretar el número.",
    "Vacíos": "Un vacío no se puede inventar; se marca para revisión humana.",
    "Duplicados": "Es un duplicado exacto por liquidacion_id + Número y puede eliminarse.",
    "Texto inconsistente": "La categoría es recuperable normalizando mayúsculas y espacios.",
    "Fuera de rango o incoherente": "El valor no tiene soporte para corregirse; se marca.",
    "Integridad entre tablas": "La relación entre tablas debe revisarse; se marca, no se corrige.",
    "Negocio": "Es una observación de negocio; se marca para el análisis.",
}

_RIESGO = {
    "Tipo de dato incorrecto": "Si no se corrige, las sumas y promedios quedarían sesgados.",
    "Vacíos": "Si no se marca, se asumirían valores inexistentes.",
    "Duplicados": "Si no se elimina, el total se contaría dos veces.",
    "Texto inconsistente": "Si no se normaliza, las categorías se fragmentarían.",
    "Fuera de rango o incoherente": "Si no se marca, el análisis incluiría datos imposibles.",
    "Integridad entre tablas": "Si no se marca, podría analizarse un animal sin liquidación.",
    "Negocio": "Si no se atiende, se perdería una señal relevante del negocio.",
}


def proponer_reglas(hallazgos):
    """Construye una propuesta de reglas determinista a partir de los hallazgos."""
    reglas = []
    for h in hallazgos:
        familia = h["familia"]
        accion = FAMILIA_A_ACCION.get(familia, "Marcar")
        reglas.append({
            "hallazgo_id": h["id"],
            "accion": accion,
            "justificacion": _JUSTIFICACION.get(familia, "Se marca por precaución."),
            "riesgo_si_no_se_trata": _RIESGO.get(familia, "El hallazgo quedaría sin atender."),
        })
    return {"reglas": reglas, "alertas_seguridad": []}


def verificar_propuestas(propuesta, hallazgos, bitacora):
    """Python: marca hallazgos inexistentes y compara acción propuesta vs aplicada."""
    reglas = propuesta.reglas if hasattr(propuesta, "reglas") else propuesta.get("reglas", [])
    por_id = {h["id"]: h for h in hallazgos}
    aplicada_por_accion = {}
    for b in bitacora:
        aplicada_por_accion.setdefault(b["accion"], b["regla"])

    verificadas = []
    for r in reglas:
        hid = r.hallazgo_id if hasattr(r, "hallazgo_id") else r["hallazgo_id"]
        accion = r.accion if hasattr(r, "accion") else r["accion"]
        justificacion = r.justificacion if hasattr(r, "justificacion") else r["justificacion"]
        existe = hid in por_id
        familia = por_id[hid]["familia"] if existe else None
        aplicada = FAMILIA_A_ACCION.get(familia, "Marcar")
        regla_id = aplicada_por_accion.get(aplicada, "—")
        verificadas.append({
            "hallazgo_id": hid,
            "accion": accion,
            "aplicada": f"{regla_id} ({aplicada})",
            "estado": "existe" if existe else "hallazgo inexistente",
            "coincide": (accion == aplicada) if existe else None,
            "justificacion": justificacion,
        })
    return verificadas


def _miles(valor):
    """Formatea un número en convención de Costa Rica: 8.292.500,00."""
    return f"{float(valor):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def redactar_informe(cifras, bitacora, veredicto):
    """Redacta el informe de calidad con cifras verificables (sin IA)."""
    filas = cifras.get("filas")
    llaves = cifras.get("llaves_unicas")
    resumen = (
        f"La validación de la base de detalle concluyó con veredicto {veredicto}. "
        f"El detalle tiene {filas} filas y {llaves} llaves únicas por liquidacion_id + Número. "
        f"La suma de Total colones es {_miles(cifras.get('suma_total_colones', 0))} y el "
        f"TOTAL NETO A PAGAR de cabecera es {_miles(cifras.get('total_neto_a_pagar', 0))}. "
        f"El peso pie suma {_miles(cifras.get('suma_peso_pie', 0))} kg y el peso canal "
        f"{_miles(cifras.get('suma_peso_canal', 0))} kg."
    )

    riesgos = []
    for b in bitacora:
        if int(b["filas_afectadas"]) > 0:
            riesgos.append(
                f"{b['regla']} ({b['accion']}): alcanza {b['filas_afectadas']} filas; "
                f"{b['descripcion']}."
            )
    if not riesgos:
        riesgos.append("No se registraron filas afectadas por las reglas de limpieza.")

    recomendaciones = [
        f"Revisar las {filas} filas de la base antes de aprobar el análisis.",
        f"Confirmar el TOTAL NETO A PAGAR de {_miles(cifras.get('total_neto_a_pagar', 0))} "
        f"contra la cabecera de la liquidación.",
        f"Validar los {_miles(cifras.get('total_deducciones', 0))} de deducciones y los "
        f"{_miles(cifras.get('total_bonos', 0))} de bonos incluidos en el pago.",
    ]

    return {"resumen_ejecutivo": resumen,
            "riesgos_para_el_analisis": riesgos,
            "recomendaciones": recomendaciones}


_NUM = re.compile(r"\d[\d.,]*")
_ANIO = re.compile(r"^(19|20)\d{2}$")


def _candidatos(token):
    token = token.strip().strip(".,;:")
    if not token:
        return set()
    valores = set()

    def f(t):
        try:
            return float(t.replace(",", "").replace(" ", "")) if "," not in t else float(t.replace(",", "."))
        except ValueError:
            return None

    if "," in token and "." in token:
        if token.rfind(",") > token.rfind("."):        # 1.234,56
            valores.add(f(token.replace(".", "").replace(",", ".")))
        else:                                            # 1,234.56
            valores.add(f(token.replace(",", "")))
    elif "," in token:
        valores.add(f(token.replace(",", "")))           # miles
        valores.add(f(token.replace(",", ".")))          # decimal
    elif "." in token:
        valores.add(f(token))
        valores.add(f(token.replace(".", "")))
    else:
        valores.add(f(token))
    return {v for v in valores if v is not None}


def _permitidos(cifras, bitacora):
    valores = set()
    for v in cifras.values():
        try:
            valores.add(float(v))
        except (TypeError, ValueError):
            pass
    for b in bitacora:
        try:
            valores.add(float(b["filas_afectadas"]))
        except (TypeError, ValueError):
            pass
    return valores


def _existe(valor, permitidos):
    for p in permitidos:
        if abs(valor - p) <= max(0.5, 0.005 * abs(p)):
            return True
    return False


def verificar_cifras(informe, cifras, bitacora):
    """Extrae cada número del informe y marca 'cifra no verificada' si no existe."""
    if hasattr(informe, "resumen_ejecutivo"):
        textos = [informe.resumen_ejecutivo] + list(informe.riesgos_para_el_analisis) + list(informe.recomendaciones)
    else:
        textos = [informe.get("resumen_ejecutivo", "")]
        textos += list(informe.get("riesgos_para_el_analisis", []))
        textos += list(informe.get("recomendaciones", []))

    permitidos = _permitidos(cifras, bitacora)
    verificadas, no_verificadas = [], []
    for frase in textos:
        frase = frase or ""
        for m in _NUM.finditer(frase):
            token = m.group(0)
            if m.start() > 0 and frase[m.start() - 1] in ("R", "r"):
                continue  # referencia a una regla (R1, R2, ...), no es una cifra
            limpio = token.strip(".,")
            if _ANIO.match(limpio):
                continue  # los años no cuentan como cifras
            valores = _candidatos(limpio)
            if valores and any(_existe(v, permitidos) for v in valores):
                verificadas.append({"numero": limpio, "frase": frase})
            else:
                no_verificadas.append({"numero": limpio, "frase": frase})
    return {"verificadas": verificadas, "no_verificadas": no_verificadas}


def resaltar(texto, no_verificados):
    """Devuelve HTML seguro con los números no verificados resaltados."""
    escapado = html.escape(texto or "")
    tokens = {t for t in no_verificados}

    def repl(m):
        return f'<mark class="no">{m.group(0)}</mark>' if m.group(0).strip(".,") in tokens else m.group(0)

    return _NUM.sub(repl, escapado)
