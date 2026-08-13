// © 2026 Martín Viera. Todos los derechos reservados.
/* verificar_licencia_secreto.mjs — api/_licencia.js NO puede fallar abierto.
 *
 * POR QUE EXISTE: antes, `SECRETO = process.env.LICENCIA_SECRETO || "mv-
 * amazon-fba-2026-clave-de-firma"` tenia un fallback fijo escrito en el
 * propio codigo fuente. Si en CUALQUIER entorno de Vercel (un Preview, un
 * branch nuevo, un typo en el nombre de la variable) LICENCIA_SECRETO no
 * estaba seteada, el sistema emitia y validaba licencias Pro con ese secreto
 * conocido -- cualquiera que leyera el archivo podia calcularse una licencia
 * valida para cualquier email, gratis, sin pasar por ningun pago.
 *
 * Este test fija que, sin LICENCIA_SECRETO configurada, el sistema:
 *   1. claveValida() nunca acepta ninguna clave (ni siquiera una calculada
 *      con el string vacio) -- falla cerrado, no abierto.
 *   2. generarClave() no emite una clave "rota" a un cliente que pago de
 *      verdad -- lanza en vez de devolver algo que despues nunca va a
 *      validar.
 *   3. api/licencia.js corta con 503 ANTES de intentar emitir nada.
 * Y que, CON la variable configurada (subproceso aparte: los env vars de
 * este modulo se leen una sola vez al importarlo), el circuito normal sigue
 * funcionando: una clave generada valida contra el mismo secreto.
 *
 * Uso:   node test/verificar_licencia_secreto.mjs
 */
import fs from "node:fs";
import path from "node:path";
import { execFileSync } from "node:child_process";

const RAIZ = path.join(import.meta.dirname, "..");
let fallas = 0;
const ok = (m) => console.log("OK     " + m);
const falla = (m) => { fallas++; console.error("FALLA  " + m); };

// --- sin LICENCIA_SECRETO seteada (estado por defecto de este proceso) ---
if (process.env.LICENCIA_SECRETO) {
  falla("este proceso ya tiene LICENCIA_SECRETO seteada -- el test no puede probar el caso 'sin configurar'");
} else {
  const { claveValida, generarClave, SECRETO_CONFIGURADO } = await import("../api/_licencia.js");

  if (SECRETO_CONFIGURADO === false) ok("SECRETO_CONFIGURADO es false sin la variable de entorno");
  else falla("SECRETO_CONFIGURADO deberia ser false sin LICENCIA_SECRETO");

  if (claveValida("cualquiera@ejemplo.com", "MVFBA-0000-0000-0000-0000") === false)
    ok("claveValida rechaza CUALQUIER clave sin secreto configurado");
  else falla("claveValida acepto una clave sin secreto configurado -- falla ABIERTO");

  // ni siquiera una clave calculada "a mano" con el string vacio cuela
  const crypto = await import("node:crypto");
  const hexVacio = crypto.createHmac("sha256", "").update("cualquiera@ejemplo.comMV-Amazon-Fba")
    .digest("hex").toUpperCase().slice(0, 16);
  const claveConSecretoVacio = "MVFBA-" + [hexVacio.slice(0, 4), hexVacio.slice(4, 8),
    hexVacio.slice(8, 12), hexVacio.slice(12, 16)].join("-");
  if (claveValida("cualquiera@ejemplo.com", claveConSecretoVacio) === false)
    ok("claveValida rechaza incluso la clave calculada con secreto vacio");
  else falla("claveValida acepto la clave del secreto vacio -- el 'sin fallback' no cerro nada");

  let lanzo = false;
  try { generarClave("cliente@ejemplo.com"); } catch { lanzo = true; }
  if (lanzo) ok("generarClave() lanza en vez de emitir una clave rota sin secreto");
  else falla("generarClave() NO lanzo sin secreto configurado -- emitiria una clave invalida a un cliente real");
}

// --- api/licencia.js corta ANTES de emitir si el secreto no esta configurado ---
{
  const LIC = fs.readFileSync(path.join(RAIZ, "api/licencia.js"), "utf8");
  if (/SECRETO_CONFIGURADO/.test(LIC) && /return res\.status\(503\)/.test(LIC))
    ok("api/licencia.js chequea SECRETO_CONFIGURADO y corta con 503");
  else falla("api/licencia.js no chequea SECRETO_CONFIGURADO antes de emitir");

  // el chequeo tiene que estar ANTES de los 3 call sites de generarClave(),
  // no despues -- si no, ya se habria intentado emitir (y explotado el throw
  // de mas arriba en un endpoint que el cliente ve como 500, no 503 prolijo).
  const idxChequeo = LIC.indexOf("SECRETO_CONFIGURADO) return res.status(503)");
  const idxPrimeraEmision = LIC.indexOf("generarClave(");
  if (idxChequeo !== -1 && idxPrimeraEmision !== -1 && idxChequeo < idxPrimeraEmision)
    ok("el chequeo de SECRETO_CONFIGURADO esta antes del primer generarClave()");
  else falla("el chequeo de SECRETO_CONFIGURADO no esta antes de emitir la licencia");
}

// --- sin fallback hardcodeado en el codigo fuente ---
{
  const SRC = fs.readFileSync(path.join(RAIZ, "api/_licencia.js"), "utf8");
  if (/\|\|\s*["'][^"']+["']/.test(SRC.match(/SECRETO\s*=[^\n]+/)?.[0] || ""))
    falla("_licencia.js todavia tiene un fallback hardcodeado para SECRETO");
  else ok("SECRETO no tiene ningun fallback hardcodeado en el codigo fuente");
}

// --- CON la variable configurada: el circuito normal sigue funcionando ---
// Subproceso aparte porque el env var de un modulo ESM se lee una sola vez,
// al importarlo -- no se puede "reimportar" con otro valor en este proceso.
{
  const script = `
    process.env.LICENCIA_SECRETO = "secreto-de-prueba-1234567890";
    const { generarClave, claveValida, SECRETO_CONFIGURADO } = await import("./api/_licencia.js");
    if (!SECRETO_CONFIGURADO) throw new Error("SECRETO_CONFIGURADO deberia ser true");
    const clave = generarClave("cliente@ejemplo.com");
    if (!/^MVFBA-[A-F0-9]{4}-[A-F0-9]{4}-[A-F0-9]{4}-[A-F0-9]{4}$/.test(clave))
      throw new Error("formato de clave invalido: " + clave);
    if (!claveValida("cliente@ejemplo.com", clave)) throw new Error("la clave generada no valido contra si misma");
    if (claveValida("otro@ejemplo.com", clave)) throw new Error("la clave de un email valido para otro email");
    console.log("subproceso-ok");
  `;
  try {
    const salida = execFileSync(process.execPath, ["--input-type=module", "-e", script],
      { cwd: RAIZ, encoding: "utf8" });
    if (salida.includes("subproceso-ok")) ok("con LICENCIA_SECRETO configurada, generar+validar sigue funcionando");
    else falla("el subproceso no confirmo el circuito normal: " + salida);
  } catch (e) {
    falla("el circuito normal (CON secreto) fallo: " + (e.stdout || e.message));
  }
}

console.log("");
if (fallas) {
  console.error(`FALLO: ${fallas} problema(s) en el manejo de LICENCIA_SECRETO.`);
  process.exit(1);
}
console.log("OK: LICENCIA_SECRETO no tiene fallback, falla cerrado sin configurar, y el circuito normal sigue andando.");
