// © 2026 Martín Viera. Todos los derechos reservados.
/* verificar_demo_sin_motor.mjs — La demo web publica (/app/) muestra
 * PANTALLAS, nunca el motor.
 *
 * POR QUE EXISTE
 * --------------
 * mobile/js/nucleo.js es el port fiel de agents/pricing, ganancias, exito,
 * dedicacion y capital_planner: cada formula, cada umbral y la curva de BSR,
 * en JavaScript legible. Publicarlo en /app/ era entregarle el activo de
 * ingenieria completo a cualquiera que abriera el inspector -- la competencia
 * incluida. Y no rompia nada, asi que nadie se iba a dar cuenta.
 *
 * Ahora scripts/vercel-build.sh publica nucleo-demo.js renombrado a
 * nucleo.js: misma API, resultados congelados. Este test falla si alguien
 * vuelve a copiar el real, aunque sea sin querer.
 *
 * Uso:   node test/verificar_demo_sin_motor.mjs
 */
import fs from "node:fs";
import path from "node:path";

const RAIZ = path.join(import.meta.dirname, "..");
const BUILD = fs.readFileSync(path.join(RAIZ, "scripts/vercel-build.sh"), "utf8");
const REAL = fs.readFileSync(path.join(RAIZ, "mobile/js/nucleo.js"), "utf8");
const STUB = fs.readFileSync(path.join(RAIZ, "mobile/js/nucleo-demo.js"), "utf8");

const fallos = [];
const ok = (m) => console.log("OK     " + m);
const falla = (m) => { fallos.push(m); console.log("FALLA  " + m); };

// --- 1) el build NO copia el motor real a la web ---
// Se busca la copia de nucleo.js "a secas": nucleo-demo.js es otro archivo.
if (/cp\s+[^\n]*mobile\/js\/nucleo\.js/.test(BUILD)) {
  falla("scripts/vercel-build.sh copia mobile/js/nucleo.js (el motor REAL) a " +
        "la demo publica: queda el activo de ingenieria a la vista");
} else ok("el build no copia el motor real a /app/");

if (/cp\s+mobile\/js\/nucleo-demo\.js\s+landing\/app\/js\/nucleo\.js/.test(BUILD)) {
  ok("  publica el stub renombrado a nucleo.js (la PWA no necesita cambios)");
} else {
  falla("el build no publica nucleo-demo.js como nucleo.js: la demo web " +
        "quedaria sin motor y rota, en vez de con datos de ejemplo");
}

// --- 2) el stub NO puede llevar las formulas adentro ---
// Marcadores del motor real que jamas deben aparecer en el stub. pyRound es
// el mas delator: existe solo para replicar el redondeo bancario de Python.
for (const marca of ["pyRound", "banker", "REFERRAL_PCT * ", "function breakEven"]) {
  if (STUB.includes(marca)) {
    falla(`nucleo-demo.js contiene "${marca}": se filtro logica del motor real`);
  } else ok(`  el stub no contiene "${marca}"`);
}
// El stub tiene que ser MUCHO mas chico que el motor: si se acerca, es que
// alguien le pego el original adentro.
if (STUB.length < REAL.length * 0.6) {
  ok(`  el stub pesa ${Math.round(STUB.length / 1024)} KB vs ${Math.round(REAL.length / 1024)} KB del motor`);
} else {
  falla(`nucleo-demo.js (${STUB.length} bytes) es casi tan grande como el motor ` +
        `(${REAL.length} bytes): revisar que no le hayan pegado el original`);
}

// --- 3) el stub expone la MISMA API que el motor ---
// Si falta una funcion, la demo web explota con "undefined is not a function"
// justo delante del prospecto.
const apiReal = (REAL.match(/^\s{4}([A-Za-z_$][\w$]*),?$/gm) || [])
  .map((l) => l.trim().replace(/,$/, ""));
const usadasPorApp = ["CFG", "landedCost", "evaluarPrecio", "simularGanancias",
  "evaluarExito", "estimarDedicacion", "estimarPorBsr", "estimarDemanda",
  "analizarSugerencias", "vendedoresPrincipales"];
for (const fn of usadasPorApp) {
  if (new RegExp(`\\b${fn}\\s*:`).test(STUB)) ok(`  el stub expone ${fn}()`);
  else falla(`nucleo-demo.js no expone ${fn}(), que mobile/js/app.js SI llama`);
}

// --- 4) la demo se declara como demo ---
// Regla del proyecto: nunca simular un resultado haciendolo pasar por real.
// Numeros congelados sin cartel serian exactamente eso.
if (/DEMO:\s*true/.test(STUB)) ok("el stub se marca DEMO: true");
else falla("nucleo-demo.js no se marca como demo");
if (/mv-demo-aviso/.test(BUILD)) {
  ok("  el build inyecta el cartel de 'datos de ejemplo' en la demo web");
} else {
  falla("la demo web no avisa que los numeros son fijos: viola la regla de " +
        "no simular resultados haciendolos pasar por reales");
}

// --- 4b) el motor falso NO puede viajar dentro del APK ---
// El build de Android copia mobile/ ENTERO a assets/www. Sin excluirlo, el
// motor de mentira quedaria adentro de la app que paga el cliente, al lado
// del real. Si alguna vez se cargara por error, esa persona veria numeros
// congelados como si fueran los suyos: una falla silenciosa, sin error a la
// vista, en un producto pago. Es justo la clase de bug que no se detecta.
const GRADLE = fs.readFileSync(path.join(RAIZ, "android/app/build.gradle"), "utf8");
if (/exclude\s+'js\/nucleo-demo\.js'/.test(GRADLE)) {
  ok("el APK excluye el motor falso (solo viaja el real)");
} else {
  falla("android/app/build.gradle no excluye js/nucleo-demo.js: el motor con " +
        "numeros congelados viajaria dentro del APK del cliente");
}

// --- 5) la descarga abierta quedo cerrada ---
const DESCARGA = fs.readFileSync(path.join(RAIZ, "api/descarga.js"), "utf8");
if (/redirigirA\([^)]*\)\s*;?\s*\n?\s*}\s*\n\s*const paymentId/.test(DESCARGA)) {
  falla("api/descarga.js todavia entrega el instalador con ?demo=1 sin pago");
} else ok("api/descarga.js ya no entrega el programa con ?demo=1");
if (/demo_bajo_pedido/.test(DESCARGA)) {
  ok("  ?demo=1 responde explicando que la demo ahora es 1:1");
} else falla("?demo=1 no explica que la demo pasa a ser bajo pedido");

console.log(fallos.length
  ? `\nFALLA: ${fallos.length} problema(s) — la demo publica puede estar filtrando el motor.`
  : "\nOK: la demo web muestra pantallas con datos de ejemplo, el motor real no se publica, y la descarga abierta esta cerrada.");
process.exit(fallos.length ? 1 : 0);
