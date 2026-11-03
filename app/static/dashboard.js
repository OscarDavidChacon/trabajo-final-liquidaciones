/* Dibuja el dashboard con Plotly leyendo el JSON de /dashboard/datos. */

const fmt = (n) => (n === null || n === undefined ? "—" : Number(n).toLocaleString("es-CR", { maximumFractionDigits: 2 }));
const pesos = (n) => "₡" + fmt(n);

function baseLayout(titulo) {
  return {
    title: { text: titulo, font: { color: "#e8eef5", size: 15 } },
    paper_bgcolor: "#18232f",
    plot_bgcolor: "#18232f",
    font: { color: "#cfd8e3" },
    margin: { l: 70, r: 70, t: 48, b: 50 },
    legend: { orientation: "h", y: -0.2 },
    xaxis: { color: "#9fb0c0", gridcolor: "#243444" },
    yaxis: { color: "#9fb0c0", gridcolor: "#243444" },
  };
}

function mensaje(id, texto) {
  document.getElementById(id).innerHTML =
    '<div style="display:flex;align-items:center;justify-content:center;height:100%;color:#9fb0c0">' + texto + "</div>";
}

function leer(id, texto) {
  document.getElementById(id).textContent = texto;
}

function graf1(d) {
  const liq = d.p1.por_liquidacion;
  const suma = (k) => liq.reduce((a, x) => a + Number(x[k] || 0), 0);
  const materia = suma("total_materia_prima"), bonos = suma("total_bonos");
  const iva = suma("iva"), ded = suma("total_deducciones");
  const x = ["Materia prima", "Bonos", "Ingresos", "IVA", "Deducciones", "Neto a pagar"];
  const traza = {
    type: "waterfall", orientation: "v",
    measure: ["absolute", "relative", "total", "relative", "relative", "total"],
    x, y: [materia, bonos, 0, iva, -ded, 0],
    text: [pesos(materia), pesos(bonos), "", pesos(iva), "-" + pesos(ded), pesos(d.p1.totales.neto_a_pagar)],
    textposition: "outside",
    connector: { line: { color: "#556" } },
    increasing: { marker: { color: "#3fb950" } },
    decreasing: { marker: { color: "#ff7b72" } },
    totals: { marker: { color: "#4c8bf5" } },
  };
  Plotly.newPlot("graf1", [traza], baseLayout("Del detalle al neto que se paga"));
  leer("lect1", "Materia prima " + pesos(materia) + " + bonos " + pesos(bonos) +
    "; con IVA (" + pesos(iva) + ") y menos deducciones (" + pesos(ded) + ") queda el neto " +
    pesos(d.p1.totales.neto_a_pagar) + ".");
}

function graf2(d) {
  const top = d.p2.top_por_valor;
  const categorias = top.map((t) => String(t.Número));
  const valores = top.map((t) => Number(t._total));
  const acc = top.map((t) => Number(t.pct_acumulado));
  const layout = baseLayout("Valor por animal (barras) y Pareto (línea)");
  layout.margin = { l: 95, r: 40, t: 60, b: 50 };
  layout.xaxis = { title: "Total colones", rangemode: "tozero", color: "#9fb0c0", gridcolor: "#243444" };
  layout.xaxis2 = { title: "% acumulado", overlaying: "x", side: "top", range: [0, 100], color: "#e3b341", showgrid: false };
  layout.yaxis = { type: "category", autorange: "reversed", color: "#9fb0c0", gridcolor: "#243444", automargin: true };
  layout.shapes = [{ type: "line", xref: "x2", yref: "paper", x0: 80, x1: 80,
    line: { dash: "dot", color: "#ff7b72", width: 2 } }];
  Plotly.newPlot("graf2", [
    { type: "bar", orientation: "h", name: "Total colones", x: valores, y: categorias, marker: { color: "#4c8bf5" } },
    { type: "scatter", name: "% acumulado", x: acc, y: categorias, xaxis: "x2", mode: "lines+markers", line: { color: "#e3b341" } },
  ], layout);
  const n80 = acc.findIndex((v) => v >= 80) + 1;
  leer("lect2", "El animal " + categorias[0] + " concentra el " + fmt(top[0].pct) + "% del valor; los " +
    n80 + " primeros animales suman el 80% del total.");
}

function graf3(d) {
  if (!d.p3.disponible) {
    mensaje("graf3", "Serie no disponible: " + (d.p3.motivo || "") + " (meses: " + (d.p3.meses || []).join(", ") + ")");
    leer("lect3", "Con una sola liquidación mensual no hay serie que comparar.");
    return;
  }
  const s = d.p3.serie;
  const layout = baseLayout("Evolución mensual de rendimiento y precio");
  layout.yaxis = { title: "Rendimiento %", color: "#9fb0c0", gridcolor: "#243444" };
  layout.yaxis2 = { title: "Precio prom. KG", overlaying: "y", side: "right", color: "#e3b341", showgrid: false };
  Plotly.newPlot("graf3", [
    { type: "scatter", mode: "lines+markers", name: "Rendimiento %", x: s.map((v) => v.mes), y: s.map((v) => v.rendimiento_pct), line: { color: "#3fb950" } },
    { type: "scatter", mode: "lines+markers", name: "Precio prom. KG", x: s.map((v) => v.mes), y: s.map((v) => v.precio_promedio_kg), yaxis: "y2", line: { color: "#e3b341" } },
  ], layout);
  const ultimo = s[s.length - 1];
  leer("lect3", "Último mes (" + ultimo.mes + "): rendimiento " + fmt(ultimo.rendimiento_pct) + "% y precio " + fmt(ultimo.precio_promedio_kg) + " por kg.");
}

function graf4(d) {
  if (!d.control.disponible) {
    mensaje("graf4", "Control no disponible: " + (d.control.motivo || ""));
    leer("lect4", "Se necesitan al menos dos meses para vigilar el " + (d.control.proporcion_vigilada || "") + ".");
    return;
  }
  const c = d.control;
  const meses = Object.keys(c.serie);
  const valores = meses.map((m) => Number(c.serie[m]));
  const colores = meses.map((m) => (c.meses_fuera_de_control.includes(m) ? "#ff7b72" : "#4c8bf5"));
  const layout = baseLayout("Control del " + c.proporcion_vigilada);
  layout.shapes = [
    { type: "line", xref: "paper", y0: c.media, y1: c.media, line: { color: "#3fb950", dash: "dash" } },
    { type: "line", xref: "paper", y0: c.limite_superior, y1: c.limite_superior, line: { color: "#ff7b72", dash: "dot" } },
  ];
  Plotly.newPlot("graf4", [{ type: "bar", x: meses, y: valores, marker: { color: colores }, name: c.proporcion_vigilada }], layout);
  leer("lect4", "Media " + fmt(c.media) + "% · límite superior " + fmt(c.limite_superior) +
    "% (media + 2 desviaciones) · meses fuera: " + (c.meses_fuera_de_control.join(", ") || "ninguno") + ".");
}

function hist(d) {
  const h = d.distribuciones.histograma;
  const centros = h.bordes.slice(0, -1).map((b, i) => (b + h.bordes[i + 1]) / 2);
  const anchos = h.bordes.slice(0, -1).map((b, i) => h.bordes[i + 1] - b);
  const layout = baseLayout("Distribución de Total colones (20 clases)");
  layout.shapes = [{ type: "line", xref: "x", yref: "paper", x0: d.distribuciones.mediana, x1: d.distribuciones.mediana,
    line: { color: "#e3b341", dash: "dash", width: 2 } }];
  Plotly.newPlot("hist", [{ type: "bar", x: centros, y: h.conteos, width: anchos, marker: { color: "#8957e5" } }], layout);
  leer("lect5", "Mediana " + pesos(d.distribuciones.mediana) + "; media " + pesos(d.distribuciones.media) +
    ". La mitad de los animales está por debajo de la mediana.");
}

fetch("/dashboard/datos")
  .then((r) => r.json())
  .then((d) => {
    if (d.error) { ["graf1", "graf2", "graf3", "graf4", "hist"].forEach((id) => mensaje(id, d.error)); return; }
    graf1(d); graf2(d); graf3(d); graf4(d); hist(d);
  })
  .catch((e) => mensaje("graf1", "Error al cargar datos: " + e));
