"""Informe gerencial sin IA + verificación de cifras en Python.

Reemplaza al antiguo agente de Gemini: el informe se redacta con plantillas en
Python a partir del análisis del dashboard. Python verifica cada número del
informe contra las cifras calculadas (tolerancia 0,5 %); si un número no existe,
queda marcado como "cifra no verificada".
"""

import html
import re

from .agente_calidad import _ANIO, _NUM, _candidatos, _existe

_ORDINALES = ["primera", "segunda", "tercera", "cuarta", "quinta", "sexta",
              "séptima", "octava", "novena", "décima"]


def preparar_cifras(resultado_analisis):
    """Texto compacto con KPIs y tablas resumidas (máx 15 filas). Nunca identificadores (I1)."""
    r = resultado_analisis
    lineas = ["KPIs del universo de análisis:"]
    for k, v in r["kpis"].items():
        lineas.append(f"  - {k}: {v}")

    lineas.append("P1 conciliación (totales):")
    for k, v in r["p1"]["totales"].items():
        lineas.append(f"  - {k}: {v}")
    lineas.append("P1 por liquidación (sin identificadores):")
    for i, x in enumerate(r["p1"]["por_liquidacion"], 1):
        lineas.append(f"  - Liquidación {i} ({x['mes']}): ingresos {x['total_ingresos']}, IVA {x['iva']}, "
                      f"deducciones {x['total_deducciones']}, neto {x['total_neto_a_pagar']}, "
                      f"suma del detalle {x['suma_detalle_total_colones']}")

    p2 = r["p2"]
    lineas.append("P2 valor y rendimiento:")
    lineas.append(f"  - total colones: {p2['total_colones']}; animales: {p2['n_animales']}; "
                  f"peso pie: {p2['peso_pie_total']}; peso canal: {p2['peso_canal_total']}; "
                  f"rendimiento ponderado %: {p2['rendimiento_ponderado_pct']}; "
                  f"rendi promedio %: {p2['rendi_promedio_pct']}; precio promedio kg: {p2['precio_promedio_kg']}")
    lineas.append(f"  - por clasificación: {p2['por_clasificacion']}")
    lineas.append("  - valores por animal (solo montos, de mayor a menor, máx 15):")
    for i, x in enumerate(p2["top_por_valor"][:15], 1):
        lineas.append(f"      {i}. {x['_total']} ({x['pct']}% del total, {x['pct_acumulado']}% acumulado)")

    lineas.append("P3 comparación mensual:")
    if r["p3"]["disponible"]:
        for x in r["p3"]["serie"]:
            lineas.append(f"  - {x['mes']}: rendimiento % {x['rendimiento_pct']}, "
                          f"precio kg {x['precio_promedio_kg']}, total {x['suma_total_colones']}")
    else:
        lineas.append(f"  - NO DISPONIBLE: {r['p3']['motivo']} (meses: {r['p3']['meses']})")

    d = r["distribuciones"]
    lineas.append("Distribución de Total colones:")
    lineas.append(f"  - cuartiles: {d['cuartiles']}; media: {d['media']}; mediana: {d['mediana']}")

    c = r["control"]
    lineas.append("Control:")
    if c["disponible"]:
        lineas.append(f"  - {c['proporcion_vigilada']}: media {c['media']}, "
                      f"límite superior {c['limite_superior']}, fuera de control: {c['meses_fuera_de_control']}")
    else:
        lineas.append(f"  - NO DISPONIBLE: {c['motivo']}")
    return "\n".join(lineas)


def _miles(valor):
    """Formatea en convención de Costa Rica: 8.292.500,00. None -> texto sin cifras."""
    if valor is None:
        return "cifra no disponible"
    return f"{float(valor):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def _ordinal(i):
    return _ORDINALES[i - 1] if 1 <= i <= len(_ORDINALES) else "siguiente"


def _redactar_markdown(r):
    """Construye el informe gerencial con estructura fija (I4), sin IA.

    Solo se citan valores presentes en el diccionario del análisis, de modo que
    ``verificar_cifras`` no marque ningún número. No se usan índices numéricos
    (listas) para no introducir cifras ficticias.
    """
    k = r.get("kpis", {})
    p1 = r.get("p1", {})
    tot = p1.get("totales", {})
    p2 = r.get("p2", {})
    p3 = r.get("p3", {})
    d = r.get("distribuciones", {})
    ctrl = r.get("control", {})

    lineas = [
        "## Resumen ejecutivo",
        f"- El universo de análisis tiene {_miles(k.get('filas_universo'))} filas y "
        f"{_miles(k.get('liquidaciones_unicas'))} liquidación(es).",
        f"- La suma de Total colones es {_miles(k.get('suma_total_colones'))}, con promedio "
        f"{_miles(k.get('promedio_total_colones'))} y mediana {_miles(k.get('mediana_total_colones'))}.",
        f"- El rendimiento ponderado (canal/pie) es {_miles(k.get('rendimiento_ponderado_pct'))} % y el "
        f"{_miles(k.get('pct_filas_marcadas'))} % de las filas quedó marcada por las reglas.",
        "",
        "## Conciliación de la liquidación",
        f"- Ingresos totales del detalle: {_miles(tot.get('ingresos'))}; neto a pagar de cabecera: "
        f"{_miles(tot.get('neto_a_pagar'))}.",
        f"- Suma del detalle (Total colones): {_miles(tot.get('suma_detalle_total_colones'))}.",
    ]
    for i, x in enumerate(p1.get("por_liquidacion", []), 1):
        lineas.append(
            f"- Liquidación {_ordinal(i)}: ingresos {_miles(x.get('total_ingresos'))}, "
            f"IVA {_miles(x.get('iva'))}, deducciones {_miles(x.get('total_deducciones'))}, "
            f"neto {_miles(x.get('total_neto_a_pagar'))}."
        )

    lineas += [
        "",
        "## Valor y rendimiento por animal",
        f"- Animales analizados: {_miles(p2.get('n_animales'))}; valor total: {_miles(p2.get('total_colones'))}.",
        f"- Peso pie total: {_miles(p2.get('peso_pie_total'))} kg; peso canal total: "
        f"{_miles(p2.get('peso_canal_total'))} kg.",
        f"- Rendimiento ponderado: {_miles(p2.get('rendimiento_ponderado_pct'))} %; rendimiento promedio: "
        f"{_miles(p2.get('rendi_promedio_pct'))} %.",
        f"- Precio promedio por kg: {_miles(p2.get('precio_promedio_kg'))}.",
    ]
    for clasif, conteo in (p2.get("por_clasificacion") or {}).items():
        lineas.append(f"- Clasificación {clasif}: {_miles(conteo)} animales.")
    top = p2.get("top_por_valor") or []
    if top:
        lineas.append("- Animales de mayor valor (Pareto):")
        for x in top[:5]:
            lineas.append(f"  - {_miles(x.get('_total'))} ({_miles(x.get('pct'))} % del total, "
                          f"{_miles(x.get('pct_acumulado'))} % acumulado).")

    lineas += ["", "## Comparación mensual"]
    if p3.get("disponible"):
        for x in p3.get("serie", []):
            lineas.append(f"- Rendimiento {_miles(x.get('rendimiento_pct'))} %, precio kg "
                          f"{_miles(x.get('precio_promedio_kg'))}, total {_miles(x.get('suma_total_colones'))}.")
    else:
        lineas.append(f"- {p3.get('motivo', 'cifra no disponible')}")

    lineas += [
        "",
        "## Alertas",
        f"- {_miles(k.get('pct_filas_marcadas'))} % de las filas requiere revisión antes de usar la base.",
        f"- La mediana de Total colones ({_miles(d.get('mediana'))}) frente a la media "
        f"({_miles(d.get('media'))}) indica la concentración del valor.",
    ]
    if ctrl.get("disponible"):
        lineas.append(f"- Límite superior del control: {_miles(ctrl.get('limite_superior'))}.")

    lineas += [
        "",
        "## Recomendaciones",
        f"- Revisar las filas marcadas ({_miles(k.get('pct_filas_marcadas'))} % del universo) antes de aprobar.",
        f"- Confirmar el neto a pagar de {_miles(tot.get('neto_a_pagar'))} contra la suma del detalle "
        f"({_miles(tot.get('suma_detalle_total_colones'))}).",
        f"- Vigilar el rendimiento ponderado ({_miles(p2.get('rendimiento_ponderado_pct'))} %) frente al "
        f"precio promedio por kg ({_miles(p2.get('precio_promedio_kg'))}).",
    ]
    return "\n".join(lineas)


def _todos_los_numeros(obj):
    """Recolecta todos los valores numéricos del diccionario de análisis."""
    valores = set()

    def recorrer(o):
        if isinstance(o, dict):
            for v in o.values():
                recorrer(v)
        elif isinstance(o, list):
            for v in o:
                recorrer(v)
        elif isinstance(o, bool):
            return
        elif isinstance(o, (int, float)):
            valores.add(float(o))
        elif isinstance(o, str):
            for token in _NUM.findall(o):
                for v in _candidatos(token):
                    valores.add(v)

    recorrer(obj)
    return valores


def verificar_cifras(informe, resultado_analisis):
    """Extrae cada número del informe y marca 'cifra no verificada' si no existe (tol. 0,5 %)."""
    permitidos = _todos_los_numeros(resultado_analisis)
    verificadas, no_verificadas = [], []
    for linea in (informe or "").splitlines():
        for m in _NUM.finditer(linea):
            token = m.group(0)
            if m.start() > 0 and linea[m.start() - 1] in ("R", "r"):
                continue  # referencia a una regla (R1, R2, ...)
            limpio = token.strip(".,")
            if _ANIO.match(limpio):
                continue  # años y meses no cuentan como cifras
            valores = _candidatos(limpio)
            if valores and any(_existe(v, permitidos) for v in valores):
                verificadas.append({"numero": limpio, "frase": linea.strip()})
            else:
                no_verificadas.append({"numero": limpio, "frase": linea.strip()})
    return {"verificadas": verificadas, "no_verificadas": no_verificadas}


def generar(resultado_analisis):
    """Ejecuta las tres funciones y devuelve {informe, verificadas, no_verificadas}."""
    cifras_texto = preparar_cifras(resultado_analisis)
    informe = _redactar_markdown(resultado_analisis)
    revision = verificar_cifras(informe, resultado_analisis)
    return {"informe": informe, "verificadas": revision["verificadas"],
            "no_verificadas": revision["no_verificadas"], "cifras_texto": cifras_texto}


# --- render mínimo de Markdown (sin dependencias) ---

def _inline(texto):
    t = html.escape(texto)
    t = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", t)
    t = re.sub(r"(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)", r"<em>\1</em>", t)
    return t


def renderizar_markdown(texto):
    """Convierte un subconjunto de Markdown a HTML seguro (títulos, listas, negrita)."""
    salida, en_lista = [], False
    for linea in (texto or "").splitlines():
        if linea.strip() == "":
            if en_lista:
                salida.append("</ul>")
                en_lista = False
            continue
        titulo = re.match(r"^(#{1,6})\s+(.*)$", linea)
        if titulo:
            if en_lista:
                salida.append("</ul>")
                en_lista = False
            nivel = min(len(titulo.group(1)) + 1, 6)
            salida.append(f"<h{nivel}>{_inline(titulo.group(2))}</h{nivel}>")
            continue
        item = re.match(r"^\s*[-*]\s+(.*)$", linea)
        if item:
            if not en_lista:
                salida.append("<ul>")
                en_lista = True
            salida.append(f"<li>{_inline(item.group(1))}</li>")
            continue
        if en_lista:
            salida.append("</ul>")
            en_lista = False
        salida.append(f"<p>{_inline(linea)}</p>")
    if en_lista:
        salida.append("</ul>")
    return "\n".join(salida)
