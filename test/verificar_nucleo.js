/* verificar_nucleo.js — Prueba de regresion del motor de negocio portado.
 *
 * Corre el motor JavaScript (mobile/js/nucleo.js) con los MISMOS inputs que el
 * motor Python (agents/*) y compara CADA campo contra la salida de referencia
 * (test/nucleo_referencia.json, generada desde Python). Deben dar identico:
 * hasta el centavo, la unidad y la redaccion de los textos.
 *
 * Uso:   node test/verificar_nucleo.js      (sale 0 si todo coincide, 1 si no)
 *
 * La referencia se regenera desde Python con test/generar_referencia.py cuando
 * cambian las formulas en agents/. */

const fs = require("fs");
const path = require("path");
const MV = require("../mobile/js/nucleo.js");

const ref = JSON.parse(
  fs.readFileSync(path.join(__dirname, "nucleo_referencia.json"), "utf8"));
const IN = ref.inputs;
const ESP = ref.esperado;

// --- reproducir la misma corrida que el harness de Python ---
const got = {};
got.pricing = MV.evaluarPrecio(IN.pricing.prod, null, IN.pricing.precio_competencia);
got.ganancias = MV.simularGanancias({
  inversion: IN.ganancias.inversion, costo: IN.ganancias.costo, flete: IN.ganancias.flete,
  arancel_pct: IN.ganancias.arancel_pct, prep: IN.ganancias.prep,
  precio: IN.ganancias.precio, techo_demanda: IN.ganancias.techo_demanda,
});
got.exito = MV.evaluarExito(IN.exito.keyword, IN.exito.competencia, IN.exito.interes_kw,
  IN.exito.precio_objetivo, IN.exito.margen_pct);
got.dedicacion = MV.estimarDedicacion(IN.dedicacion.n_op, IN.dedicacion.lanzando);
const landed = MV.landedCost(IN.pricing.prod.costo, IN.pricing.prod.flete,
  IN.pricing.prod.arancel_pct, IN.pricing.prod.prep);
const netUnit = IN.caja.precio - IN.caja.precio * 0.15 - 3.65 - IN.caja.precio * 0.10 - landed;
got.caja = MV.proyeccionRealista(IN.caja.budget, landed, IN.caja.precio, netUnit,
  { techo_demanda: IN.caja.techo_demanda });

// --- comparacion profunda (tolerancia 0.011 para floats) ---
// --- estimacion por BSR: la app movil la hace OFFLINE, asi que tiene que dar
// EXACTAMENTE el mismo numero que la PC (si no, el mismo producto mostraria
// ventas distintas segun donde lo mires) ---
got.bsr_curva = IN.bsr_curva.map((b) => MV.ventasDesdeBsr(b));
got.bsr_categorias = IN.bsr_categorias.map(([b, c]) => MV.ventasDesdeBsr(b, c));
got.bsr_confianza = IN.bsr_categorias.map(([b, c]) => MV.confianzaBsr(b, c));
got.bsr_textos = IN.bsr_textos.map((t) => {
  const r = MV.estimarPorBsr(t);
  return { ok: r.ok, bsr: r.bsr, categoria: r.categoria,
           ventas_estim: r.ventas_estim, confianza: r.confianza };
});
got.potencial = IN.potencial.map((caso) => MV.potencialProducto(caso));
const vend = MV.vendedoresPrincipales(IN.vendedores);
got.vendedores = {
  ok: vend.ok, ventas_estim_total: vend.ventas_estim_total,
  ventas_estim_lider: vend.ventas_estim_lider,
  productos: vend.productos.map((p) => ({
    asin: p.asin, bsr: p.bsr, categoria: p.categoria, precio: p.precio,
    ventas_estim: p.ventas_estim, confianza: p.confianza, cuota_pct: p.cuota_pct,
    ingreso_estim_mes: p.ingreso_estim_mes, potencial: p.potencial,
    potencial_parcial: p.potencial_parcial,
  })),
};

const diffs = [];
function walk(a, b, p) {
  if (a && b && typeof a === "object" && typeof b === "object" && !Array.isArray(a)) {
    const keys = new Set([...Object.keys(a), ...Object.keys(b)]);
    for (const k of keys) {
      if (!(k in a)) diffs.push(`${p}.${k}: falta en referencia`);
      else if (!(k in b)) diffs.push(`${p}.${k}: falta en JS`);
      else walk(a[k], b[k], `${p}.${k}`);
    }
  } else if (Array.isArray(a) && Array.isArray(b)) {
    if (a.length !== b.length) diffs.push(`${p}: largo ${a.length} vs ${b.length}`);
    for (let i = 0; i < Math.min(a.length, b.length); i++) walk(a[i], b[i], `${p}[${i}]`);
  } else if (typeof a === "number" && typeof b === "number") {
    if (Math.abs(a - b) > 0.011) diffs.push(`${p}: ${a} vs ${b}`);
  } else if (a !== b) {
    diffs.push(`${p}: ${JSON.stringify(a)} vs ${JSON.stringify(b)}`);
  }
}
for (const sec of Object.keys(ESP)) walk(ESP[sec], got[sec], sec);

if (diffs.length) {
  console.error(`FALLO: ${diffs.length} diferencia(s) motor JS vs Python:`);
  diffs.slice(0, 40).forEach((d) => console.error("  " + d));
  process.exit(1);
}
console.log("OK: motor JS identico al motor Python en pricing, ganancias, exito, "
  + "dedicacion, caja, curva BSR, parseo de BSR, potencial y vendedores.");
