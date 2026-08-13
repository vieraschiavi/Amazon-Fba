// © 2026 Martín Viera. Todos los derechos reservados.
/* verificar_sw_precache.mjs — El service worker tiene que precachear TODO lo
 * que index.html carga.
 *
 * POR QUE EXISTE: js/seguro.js se cargaba en index.html pero no estaba en la
 * lista SHELL del service worker. En caliente no se notaba (el archivo ya
 * estaba en la cache HTTP del navegador), pero en un arranque EN FRIO SIN
 * CONEXION el SW lo pedia a la red, fallaba, y escapar() quedaba sin definir:
 * la app rompia entera al primer render. Justo el modo en el que la app movil
 * tiene que funcionar mejor.
 *
 * Este test compara los <script src> y <link rel=stylesheet> del HTML contra
 * SHELL y falla si falta alguno.
 *
 * Uso:   node test/verificar_sw_precache.mjs
 */
import fs from "node:fs";
import path from "node:path";

const RAIZ = path.join(import.meta.dirname, "..");
const html = fs.readFileSync(path.join(RAIZ, "mobile/index.html"), "utf8");
const sw = fs.readFileSync(path.join(RAIZ, "mobile/service-worker.js"), "utf8");

const fallos = [];
const ok = (m) => console.log("OK     " + m);
const falla = (m) => { fallos.push(m); console.log("FALLA  " + m); };

// --- 1) que carga el HTML (solo recursos locales; los remotos no se precachean) ---
const recursos = [];
for (const m of html.matchAll(/<script[^>]+src="([^"]+)"/g)) recursos.push(m[1]);
for (const m of html.matchAll(/<link[^>]+rel="stylesheet"[^>]*href="([^"]+)"/g)) recursos.push(m[1]);
const locales = recursos.filter((r) => !/^(https?:)?\/\//.test(r));

if (!locales.length) falla("no se detecto ningun recurso local en mobile/index.html");
else ok(`mobile/index.html carga ${locales.length} recurso(s) local(es)`);

// --- 2) la lista SHELL del service worker ---
const mShell = sw.match(/const SHELL\s*=\s*\[([\s\S]*?)\]/);
if (!mShell) {
  falla("no encontre la lista SHELL en mobile/service-worker.js");
} else {
  const shell = [...mShell[1].matchAll(/"([^"]+)"/g)].map((m) => m[1]);
  ok(`SHELL precachea ${shell.length} entrada(s)`);
  // "./js/app.js" y "js/app.js" son el mismo recurso: se normaliza el "./".
  const norm = (s) => s.replace(/^\.\//, "");
  const enShell = new Set(shell.map(norm));
  for (const r of locales) {
    if (enShell.has(norm(r))) ok(`  ${r} esta precacheado`);
    else falla(`  ${r} lo carga index.html pero NO esta en SHELL (rompe offline en frio)`);
  }
}

// --- 3) la version del cache se bumpea cuando cambia el shell ---
const mCache = sw.match(/const CACHE\s*=\s*"([^"]+)"/);
if (!mCache) falla("no encontre la constante CACHE en el service worker");
else if (!/v\d+$/.test(mCache[1])) {
  falla(`CACHE "${mCache[1]}" no termina en vN: sin version no se purga el cache viejo`);
} else ok(`CACHE versionado: ${mCache[1]}`);

console.log("");
if (fallos.length) {
  console.error(`FALLO: ${fallos.length} problema(s) de precache del service worker.`);
  process.exit(1);
}
console.log("OK: el service worker precachea todo lo que index.html carga (offline en frio).");
