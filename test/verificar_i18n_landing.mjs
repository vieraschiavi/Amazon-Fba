// © 2026 Martín Viera. Todos los derechos reservados.
/* verificar_i18n_landing.mjs — Test de regresion del i18n de la landing.
 *
 * landing/index.html es trilingüe: cada texto vive en un data-t="clave" y el
 * diccionario I18N tiene un bloque por idioma (es/en/pt). Hay dos formas
 * silenciosas de romperlo, y las dos pasan desapercibidas en el navegador
 * porque applyLang simplemente no toca el elemento y queda el texto en
 * español:
 *
 *   1. agregar copy nuevo en es/ y olvidarse de en/ o pt/  -> el visitante
 *      en ingles ve media pagina en castellano;
 *   2. poner un data-t en el HTML sin agregar la clave a NINGUN diccionario
 *      -> ese texto no se traduce nunca, en ningun idioma.
 *
 * Este test compara los tres diccionarios entre si Y contra los data-t
 * realmente usados en el HTML. Motivado por la comparacion nombrando a
 * Helium 10 / Jungle Scout, que sumo 20 claves nuevas de una sola vez.
 *
 * Uso:   node test/verificar_i18n_landing.mjs
 */
import fs from "node:fs";
import path from "node:path";

const RUTA = path.join(import.meta.dirname, "..", "landing", "index.html");
const html = fs.readFileSync(RUTA, "utf8");

// --- claves usadas en el HTML (data-t="...") ---
const enHtml = new Set([...html.matchAll(/data-t="([^"]+)"/g)].map((m) => m[1]));

// --- diccionarios: const I18N = { es:{...}, en:{...}, pt:{...} } ---
// Se extrae cada bloque por su etiqueta de idioma y se listan sus claves
// "xxx": (sin evaluar el JS, para no ejecutar nada del archivo).
function clavesDe(idioma) {
  const re = new RegExp(`\\n\\s{2}${idioma}\\s*:\\s*\\{`, "");
  const m = re.exec(html);
  if (!m) return null;
  let i = m.index + m[0].length, prof = 1;
  const desde = i;
  while (i < html.length && prof > 0) {
    if (html[i] === "{") prof++;
    else if (html[i] === "}") prof--;
    i++;
  }
  const cuerpo = html.slice(desde, i - 1);
  return new Set([...cuerpo.matchAll(/"([a-zA-Z0-9_.]+)"\s*:/g)].map((x) => x[1]));
}

const IDIOMAS = ["es", "en", "pt"];
const dicts = {};
let fallas = 0;

for (const idioma of IDIOMAS) {
  const c = clavesDe(idioma);
  if (!c || c.size === 0) {
    console.error(`FALLA  no se pudo leer el diccionario "${idioma}" de landing/index.html`);
    fallas++;
  } else {
    dicts[idioma] = c;
    console.log(`OK     diccionario ${idioma}: ${c.size} claves`);
  }
}

if (fallas) { console.error("\nNo se pudieron leer los 3 diccionarios."); process.exit(1); }

// --- 1) los 3 idiomas tienen exactamente las mismas claves ---
const base = dicts.es;
for (const idioma of ["en", "pt"]) {
  const faltan = [...base].filter((k) => !dicts[idioma].has(k));
  const sobran = [...dicts[idioma]].filter((k) => !base.has(k));
  if (faltan.length) {
    console.error(`FALLA  ${idioma}: faltan ${faltan.length} clave(s) que si estan en es -> ${faltan.join(", ")}`);
    fallas++;
  }
  if (sobran.length) {
    console.error(`FALLA  ${idioma}: tiene ${sobran.length} clave(s) que NO estan en es -> ${sobran.join(", ")}`);
    fallas++;
  }
  if (!faltan.length && !sobran.length) {
    console.log(`OK     ${idioma} tiene exactamente las mismas claves que es`);
  }
}

// --- 2) todo data-t del HTML existe en los diccionarios ---
const huerfanas = [...enHtml].filter((k) => !base.has(k));
if (huerfanas.length) {
  console.error(`FALLA  ${huerfanas.length} data-t en el HTML sin clave en el diccionario (nunca se traducen) -> ${huerfanas.join(", ")}`);
  fallas++;
} else {
  console.log(`OK     los ${enHtml.size} data-t del HTML tienen su clave en el diccionario`);
}

if (fallas) {
  console.error(`\n${fallas} problema(s) de i18n en la landing.`);
  process.exit(1);
} else {
  console.log(`\nOK: i18n de la landing consistente — ${base.size} claves x ${IDIOMAS.length} idiomas, ${enHtml.size} data-t cubiertos.`);
  process.exit(0);
}
