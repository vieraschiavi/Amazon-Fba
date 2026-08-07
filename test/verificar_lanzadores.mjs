/* verificar_lanzadores.mjs — Test de regresion de los .bat que abren el
 * programa en Windows.
 *
 * QUE PASO (por eso existe este test): la deteccion de Python estaba copiada
 * en cada .bat y se desincronizo. Dos quedaron con fallback al Python del
 * sistema y CUATRO cortaban con "[ERROR] Falta el runtime de Python embebido"
 * sin ofrecer salida. Como runtime/ NO esta en el repositorio (lo arma el
 * instalador), cualquiera que baje el codigo y haga doble clic en INICIAR.bat
 * se quedaba sin poder abrir nada. Eso es exactamente lo que reporto el
 * usuario.
 *
 * Tambien cubre los puertos: antes se leia `netstat | findstr ":8000"`, que
 * depende del idioma de Windows y ademas hace falso positivo (":8000 " matchea
 * dentro de 18000). Ahora lo resuelve core/puerto.py con un bind real.
 *
 * No ejecuta cmd.exe (no hay Windows aca): verifica invariantes del texto de
 * los .bat, que es donde estuvo el bug.
 *
 * Uso:   node test/verificar_lanzadores.mjs
 */
import fs from "node:fs";
import path from "node:path";
import { execSync } from "node:child_process";

const RAIZ = path.join(import.meta.dirname, "..");

// Los 6 lanzadores que abren algo. Todos tienen que resolver Python igual.
const LANZADORES = [
  "INICIAR.bat", "APP_ESCRITORIO.bat", "CONECTAR.bat",
  "DIAGNOSTICO.bat", "API.bat", "LEGACY_STREAMLIT.bat",
];
// Los que levantan un servidor: ademas tienen que buscar puerto libre.
const CON_SERVIDOR = ["INICIAR.bat", "API.bat", "LEGACY_STREAMLIT.bat"];

let fallas = 0;
const ok = (m) => console.log("OK     " + m);
const mal = (m) => { console.error("FALLA  " + m); fallas++; };

// --- el helper compartido existe y expone las dos acciones ---
const helper = path.join(RAIZ, "_entorno.bat");
if (!fs.existsSync(helper)) {
  mal("_entorno.bat no existe: los lanzadores lo llaman y fallarian todos");
} else {
  const h = fs.readFileSync(helper, "utf8");
  for (const accion of ["buscar_python", "buscar_puerto"]) {
    if (h.includes(`:${accion}`)) ok(`_entorno.bat define :${accion}`);
    else mal(`_entorno.bat no define :${accion}`);
  }
  // el fallback al Python del sistema es la razon de ser del arreglo
  if (/runtime\\python\.exe/.test(h) && /Anaconda3|Programs\\Python|py -c/.test(h)) {
    ok("_entorno.bat prueba el runtime embebido Y cae al Python del sistema");
  } else {
    mal("_entorno.bat perdio el runtime embebido o el fallback al sistema");
  }
}

// --- ningun lanzador vuelve a tener deteccion propia ni a morir sin salida ---
for (const nombre of LANZADORES) {
  const p = path.join(RAIZ, nombre);
  if (!fs.existsSync(p)) { mal(`${nombre} no existe`); continue; }
  const c = fs.readFileSync(p, "utf8");

  if (c.includes("_entorno.bat")) ok(`${nombre} usa el helper compartido`);
  else mal(`${nombre} NO llama a _entorno.bat: volvio a tener deteccion propia`);

  // el bug original: "if not exist runtime\python.exe -> exit" sin alternativa
  const cortaSinSalida = /if not exist "!PYTHON!"[\s\S]{0,200}?exit \/b 1/.test(c)
    && !c.includes("_entorno.bat");
  if (cortaSinSalida) {
    mal(`${nombre} corta si falta runtime/ sin ofrecer el Python del sistema`);
  }

  // cd /d: sin el /d, un doble clic desde otra UNIDAD (D:) no cambia de disco
  if (/^cd \/d /m.test(c)) ok(`${nombre} usa "cd /d" (funciona instalado en D:)`);
  else mal(`${nombre} usa "cd" sin /d: se rompe si se instala en otro disco`);
}

// --- nadie vuelve a decidir el puerto con netstat ---
for (const nombre of LANZADORES) {
  const c = fs.readFileSync(path.join(RAIZ, nombre), "utf8");
  // netstat en un comentario explicativo esta bien; ejecutarlo no.
  const ejecuta = c.split("\n").some((l) =>
    l.includes("netstat") && !/^\s*(rem|::)/i.test(l.trim()));
  if (ejecuta) mal(`${nombre} vuelve a decidir el puerto parseando netstat`);
}
if (!fallas) ok("ningun lanzador decide el puerto parseando netstat");

// --- los que levantan servidor buscan puerto libre y no fijan el 8000 ---
for (const nombre of CON_SERVIDOR) {
  const c = fs.readFileSync(path.join(RAIZ, nombre), "utf8");
  if (/buscar_puerto/.test(c)) ok(`${nombre} busca un puerto libre antes de arrancar`);
  else mal(`${nombre} levanta un servidor sin chequear si el puerto esta ocupado`);
  // no debe quedar un --port 8000 fijo
  if (/--port\s+8000\b/.test(c) || /--server\.port\s+8501\b/.test(c)) {
    mal(`${nombre} todavia fija el puerto a mano en vez de usar el libre`);
  }
}

// --- core/puerto.py existe y se instala (viaja por ..\core\*) ---
if (fs.existsSync(path.join(RAIZ, "core", "puerto.py"))) {
  ok("core/puerto.py existe (y el instalador lo copia por ..\\core\\*)");
} else {
  mal("falta core/puerto.py: buscar_puerto no podria resolver nada");
}

// --- finales de linea: TODO script de Windows tiene que ir en CRLF ---
// cmd.exe avanza por posicion de BYTE dando por sentado CRLF. Con LF le falta
// un byte por linea y el desfasaje se ACUMULA: la primera sale entera, la
// siguiente pierde 1 caracter, la siguiente 2... En la consola del cliente se
// ve como  'cho' no se reconoce como un comando  /  'ho' ...  /  'o' ...
// El .bat se lee perfecto en un editor, asi que no hay forma de notarlo sin
// ejecutarlo en un Windows real -- exactamente como paso. .gitattributes lo
// fija con "-text" (el CRLF vive en el blob); esto verifica que asi sea.
const scripts = execSync("git ls-files '*.bat' '*.cmd' '*.ps1' '*.vbs'",
  { cwd: RAIZ, encoding: "utf8" }).split("\n").filter(Boolean);
if (!scripts.length) mal("no encontre ningun script de Windows para chequear");
for (const rel of scripts) {
  const b = fs.readFileSync(path.join(RAIZ, rel));
  const lf = (b.toString("latin1").match(/\n/g) || []).length;
  const crlf = (b.toString("latin1").match(/\r\n/g) || []).length;
  if (lf && crlf === lf) ok(`${rel} en CRLF`);
  else if (!crlf) {
    mal(`${rel} esta en LF: cmd.exe se come los primeros caracteres de cada ` +
        "linea y el usuario ve 'cho'/'ho'/'o' no se reconoce como un comando");
  } else {
    mal(`${rel} mezcla CRLF y LF (${crlf}/${lf}): se rompe a partir de la ` +
        "primera linea con LF suelto");
  }
}
// El .gitattributes es lo que mantiene el CRLF vivo al clonar/bajar el ZIP.
const ATTRS = fs.existsSync(path.join(RAIZ, ".gitattributes"))
  ? fs.readFileSync(path.join(RAIZ, ".gitattributes"), "utf8") : "";
for (const ext of ["bat", "cmd", "ps1", "vbs"]) {
  if (new RegExp(`^\\s*\\*\\.${ext}\\s+-text\\s*$`, "m").test(ATTRS)) {
    ok(`  .gitattributes congela *.${ext} con -text`);
  } else {
    mal(`.gitattributes no protege *.${ext}: git puede volver a normalizar a ` +
        "LF y el script vuelve a romperse en Windows sin que nadie lo toque");
  }
}

if (fallas) {
  console.error(`\n${fallas} problema(s) en los lanzadores.`);
  process.exit(1);
} else {
  console.log(`\nOK: los ${LANZADORES.length} lanzadores comparten la deteccion de Python (runtime embebido + fallback), usan "cd /d" y no fijan puertos.`);
  process.exit(0);
}
