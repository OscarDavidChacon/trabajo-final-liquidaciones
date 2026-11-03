"""Pruebas del informe gerencial: redacción determinista y verificación en Python."""

from app.services.agente_informe import (generar, preparar_cifras,
                                         renderizar_markdown, verificar_cifras)

ANALISIS = {
    "kpis": {"suma_total_colones": 8292500.0, "subtotal": 4185995.54, "filas_universo": 20,
             "rendimiento_ponderado_pct": 53.6},
    "p1": {"totales": {"neto_a_pagar": 8348187.11, "ingresos": 8292500.0},
           "por_liquidacion": [{"mes": "2026-10", "total_ingresos": 4144550.0, "iva": 41445.54,
                                "total_deducciones": 14964.84, "total_neto_a_pagar": 4171030.7,
                                "suma_detalle_total_colones": 4144550.0}]},
    "p2": {"total_colones": 8292500.0, "n_animales": 20,
           "peso_pie_total": 6288.5, "peso_canal_total": 3370.5,
           "rendimiento_ponderado_pct": 53.6, "rendi_promedio_pct": 53.6,
           "precio_promedio_kg": 2443.5, "por_clasificacion": {"AA": 10, "AAA": 9, "A": 1},
           "top_por_valor": [{"Número": "10005007", "_total": 530887.5, "pct": 6.4, "pct_acumulado": 6.4}]},
    "p3": {"disponible": False, "meses": ["2026-10"], "motivo": "un solo mes"},
    "distribuciones": {"cuartiles": {"p25": 379137.5, "p50": 388937.5, "p75": 447665.62, "p90": 509107.5},
                       "mediana": 388937.5, "media": 414625.0},
    "control": {"disponible": False, "motivo": "un solo mes", "proporcion_vigilada": "% de filas marcadas"},
}


def test_preparar_cifras_no_incluye_identificadores():
    texto = preparar_cifras(ANALISIS)
    assert "8292500.0" in texto
    assert "185247121" not in texto  # no aparece el id de liquidación


def test_verificar_cifras_correcta_e_inventada():
    informe = ("## Resumen ejecutivo\n"
               "El neto a pagar fue 8.348.187,11 colones y la mediana 388.937,50.\n"
               "Se detectaron 999 casos inexistentes.\n")
    resultado = verificar_cifras(informe, ANALISIS)
    no_ver = {x["numero"] for x in resultado["no_verificadas"]}
    ver = {x["numero"] for x in resultado["verificadas"]}
    assert "999" in no_ver
    assert "8.348.187,11" in ver
    assert "388.937,50" in ver
    assert "2026" not in no_ver  # el año no cuenta


def test_renderizar_markdown_genera_html():
    html = renderizar_markdown("## Título\n- uno\n- dos\n\n**negrita**")
    assert "<h3>Título</h3>" in html
    assert "<li>uno</li>" in html
    assert "<strong>negrita</strong>" in html


def test_generar_sin_cifras_inventadas():
    resultado = generar(ANALISIS)
    assert "## Resumen ejecutivo" in resultado["informe"]
    assert resultado["no_verificadas"] == []
