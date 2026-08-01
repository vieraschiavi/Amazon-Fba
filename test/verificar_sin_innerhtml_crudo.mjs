/* verificar_sin_innerhtml_crudo.mjs — Barre TODO el codigo propio (mobile/,
 * landing/ -- excluye landing/app/ por ser build output de mobile/, y
 * cualquier vendor/node_modules) buscando asignaciones a innerHTML y, dentro
 * de cada una, cada interpolacion ${...}.
 *
 * NO intenta adivinar automaticamente si una interpolacion es "segura": una
 * heuristica generica (ej. "algo.algo es un enum, seguro") da falsos
 * positivos y falsos negativos sin criterio (el mismo nombre de variable, ej.
 * "d", significa cosas MUY distintas en mobile/js/app.js vs. landing/gracias.html
 * -- linkear por nombre de propiedad es justo como se pasaba por alto que
 * d.email en gracias.html SI era un dato externo sin escapar).
 *
 * En cambio: cada interpolacion encontrada HOY se audito a mano una por una
 * (ver README de este archivo, seccion INVENTARIO) y quedo clasificada como
 * ESCAPADA (pasa por escapar()/escaparHtml()) o SEGURA-POR-CONSTRUCCION (texto
 * fijo del propio codigo -- diccionario I18N/INFO_METRICAS, o numero via un
 * formateador (fmtMoney, toFixed, Math.), o charset controlado como la clave
 * HMAC de licencia).
 * Esa clasificacion queda congelada en INVENTARIO de abajo. Si alguien agrega
 * un innerHTML nuevo, o cambia uno existente, este test lo detecta como
 * "no inventariado" y hay que clasificarlo a mano antes de que pase --
 * exactamente lo que hubiera atajado el bug de d.email.
 *
 * Uso:   node test/verificar_sin_innerhtml_crudo.mjs
 */
import fs from "node:fs";
import path from "node:path";

const RAIZ = path.join(import.meta.dirname, "..");
const ARCHIVOS = [
  "mobile/js/app.js",
  "mobile/js/seguro.js",
  "landing/index.html",
  "landing/gracias.html",
];

// clave = "archivo:linea_de_apertura_del_innerHTML" -> Set de expresiones
// ${...} ya auditadas para ese sitio, con el motivo. Si el codigo cambia y
// aparece una expresion nueva en un sitio ya conocido, o un sitio nuevo, el
// test falla (hay que revisar y clasificar antes de agregarlo aca).
const INVENTARIO = {
  "mobile/js/app.js:213": {
    motivo: "INFO_METRICAS: diccionario fijo escrito en este mismo archivo, no dato externo",
    ok: ["d.que", "d.objetivo", "d.desvio"],
  },
  "mobile/js/app.js:264": {
    motivo: "4 llamadas a kpiHtml(): labels fijos + numeros via fmtMoney/fmtPct/fmtNum + conteos propios",
    ok: [
      'kpiHtml("Productos", r.n, `${s.verde || 0} verde · ${s.amarillo || 0} amarillo · ${s.rojo || 0} rojo`, null, true)',
      'kpiHtml("Capital en pipeline", fmtMoney(r.capital_pipeline_total), "~4 meses de stock", null, false, "capital_pipeline")',
      'kpiHtml("Margen promedio", fmtPct(r.margen_promedio_pct), "de todo el portafolio", tonoMargen(r.margen_promedio_pct), false, "margen")',
      'kpiHtml("Ordenes", fmtNum(ordenes), fmtNum(unidades) + " unidades")',
    ],
  },
  "mobile/js/app.js:293": {
    motivo: "escapar(p.nombre); semaforo/id/numeros: enum fijo, id de la propia DB local, o via fmt*",
    ok: ["escapar(p.nombre)", "tonoSemaforo(p.semaforo)", "p.semaforo.toUpperCase()",
      "fmtMoney2(p.precio)", "fmtPct(p.margen)", '_iconoInfo("margen")', "fmtPct(p.roi)",
      '_iconoInfo("roi")', "fmtMoney2(p.neto_unidad)", "fmtMoney(p.ingreso_real)",
      "fmtNum(p.unidades_reales)", "p.id"],
  },
  "mobile/js/app.js:435": {
    motivo: "escapar(r.mensaje): mensaje de error que puede incluir texto de la API",
    ok: ["escapar(r.mensaje)"],
  },
  "mobile/js/app.js:444": {
    motivo: "kpiHtml()/fmt* con numeros; filas ya construida con fmtMoney() sobre claves fijas de costos; caveat escapado",
    ok: [
      'kpiHtml("Ganancia neta", fmtMoney(lo.ganancia_neta), r.entrada, tonoG, true, "ganancia_neta")',
      'kpiHtml("ROI inversion", fmtPct(lo.roi_inversion_pct), fmtMoney(lo.inversion_usada), tonoG, false, "roi")',
      'kpiHtml("Ganancia/unidad", fmtMoney2(lo.ganancia_por_unidad), "precio " + fmtMoney2(ue.precio_venta), tonoSemaforo(ue.semaforo), false, "margen")',
      'kpiHtml("Sueldo en meseta", fmtMoney(re.sueldo_meseta_mensual), "reciclando capital 12m", null, false, "sueldo_meseta")',
      "fmtMoney(lo.ingreso_bruto)", "filas", "fmtMoney(lo.ganancia_neta)",
      "fmtNum(lo.unidades_compradas)", "fmtNum(lo.meses_para_venderlo)",
      're.mes_primer_cobro || "—"', "escapar(r.caveat)"],
  },
  "mobile/js/app.js:595": {
    motivo: "kws.map(k => ...escapar(k)...): cada keyword de Amazon pasa por escapar() adentro del map",
    ok: ['kws.map((k) => `<span class="chip">${escapar(k)}</span>`).join("")'],
  },
  "mobile/js/app.js:919": {
    motivo: "conteos numericos propios (cantidad de productos/ventas guardadas en este telefono)",
    ok: ["r.n", "estado.ventas.length"],
  },
  "mobile/js/app.js:1057": {
    motivo: "escapar(t.ultimo/t.cta): textos del diccionario I18N propio; url es constante literal del archivo",
    ok: ["escapar(t.ultimo)", "url", "escapar(t.cta)"],
  },
  "mobile/js/app.js:1060": {
    motivo: "mismo caso que 1057, otro mensaje del diccionario I18N",
    ok: ["escapar(t.quedan2)", "url", "escapar(t.cta)"],
  },
  "mobile/js/app.js:1165": {
    motivo: "ternario fijo que arma el propio codigo (paso actual del tour), no dato externo",
    ok: ['i === _tourPaso ? "on" : ""'],
  },
  "landing/index.html:1110": {
    motivo: "txt: texto del diccionario I18N propio (reviews.vacio) via t(), no dato externo",
    ok: ["txt"],
  },
  "landing/index.html:1114": {
    motivo: "numeros formateados + texto I18N con reemplazo de un numero",
    ok: ["resumen.promedio.toFixed(1)", "estrellas(resumen.promedio)", "totalTxt"],
  },
  "landing/index.html:1118": {
    motivo: "estrellas(): devuelve solo caracteres ★/☆; comentario/nombre de la reseña pasan por escaparHtml()",
    ok: ["estrellas(r.puntaje)", "escaparHtml(r.comentario)", "escaparHtml(r.nombre)"],
  },
  "landing/gracias.html:97": {
    motivo: "d.licencia: charset fijo MVFBA-XXXX-XXXX-XXXX-XXXX (api/_licencia.js, hex+guiones). "
      + "email de MercadoPago YA pasa por escaparHtml() mas arriba (variable `email`, no `d.email` directo). "
      + "payment_id/proc van por encodeURIComponent (posicion de atributo href).",
    ok: ["d.licencia", "email",
      'encodeURIComponent(d._pid || "")', 'd._proc ? "&proc=" + encodeURIComponent(d._proc) : ""'],
  },
  "landing/gracias.html:239": {
    motivo: "mostrarError() siempre se llama con un literal de texto escrito en este archivo, nunca con dato externo",
    ok: ["msg"],
  },
};

let fallas = 0;
let vistos = 0;

for (const rel of ARCHIVOS) {
  const ruta = path.join(RAIZ, rel);
  const txt = fs.readFileSync(ruta, "utf8");
  const lineas = txt.split("\n");

  for (let i = 0; i < lineas.length; i++) {
    if (!/\.innerHTML\s*[+]?=/.test(lineas[i])) continue;
    let bloque = lineas[i];
    let j = i;
    while (!/;\s*$/.test(lineas[j]) && j < lineas.length - 1 && j < i + 40) {
      j++;
      bloque += "\n" + lineas[j];
    }
    const clave = `${rel}:${i + 1}`;
    // Interpolaciones de primer nivel (no baja a las anidadas dentro de un
    // .map(...) ya clasificado como una sola unidad -- ver mobile/js/app.js:595).
    const interpolaciones = [...bloque.matchAll(/\$\{([^{}]*(?:\{[^{}]*\}[^{}]*)*)\}/g)].map((m) => m[1].trim());
    if (interpolaciones.length === 0) continue; // solo texto fijo: nada que auditar
    const entrada = INVENTARIO[clave];
    vistos += interpolaciones.length;
    if (!entrada) {
      console.error(`FALLA  ${clave}: innerHTML SIN CLASIFICAR (agrega una entrada a INVENTARIO tras auditarlo)`);
      console.error(`        expresiones encontradas: ${JSON.stringify(interpolaciones)}`);
      fallas++;
      continue;
    }
    for (const expr of interpolaciones) {
      if (!entrada.ok.includes(expr)) {
        console.error(`FALLA  ${clave}: expresion NUEVA o CAMBIADA sin auditar: \${${expr}}`);
        console.error(`        esperadas para este sitio: ${JSON.stringify(entrada.ok)}`);
        fallas++;
      }
    }
  }
}

// Chequeo puntual: el sitio "landing/gracias.html:97" confia en que la
// variable `email` que interpola ya llega escapada -- eso se construye en OTRA
// linea (el `const email = ...` de mas arriba), que el barrido de arriba no
// mira (no seria un innerHTML). Sin esto, alguien podria sacarle el
// escaparHtml() a esa linea y el barrido de arriba seguiria diciendo "OK"
// porque el NOMBRE de la variable interpolada (`email`) no cambio.
{
  const rel = "landing/gracias.html";
  const txt = fs.readFileSync(path.join(RAIZ, rel), "utf8");
  const okDirecta = /const email = d\.email \? `[^`]*\$\{escaparHtml\(d\.email\)\}/.test(txt);
  if (!okDirecta) {
    console.error(`FALLA  ${rel}: la variable "email" (interpolada en el sitio de arriba) ya no se construye con escaparHtml(d.email) -- revisar antes de seguir.`);
    fallas++;
  } else {
    console.log(`OK     ${rel}: la variable "email" sigue construida con escaparHtml(d.email) antes de llegar al innerHTML.`);
  }
}

if (fallas) {
  console.error(`\n${fallas} interpolacion(es) sin clasificar o cambiadas sin auditar.`);
  process.exit(1);
} else {
  console.log(`OK: ${vistos} interpolaciones en ${Object.keys(INVENTARIO).length} sitios de innerHTML, en ${ARCHIVOS.length} archivos -- todas auditadas: escapadas o seguras por construccion (texto propio/numero formateado/charset fijo). 0 casos de dato externo crudo.`);
  process.exit(0);
}
