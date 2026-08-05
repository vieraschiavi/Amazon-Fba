/* verificar_licencia_dueno.mjs — La licencia de DUEÑO no se puede pedir desde
 * la web: es solo para el build de GitHub.
 *
 * POR QUE EXISTE: el camino ?dueno=1 de api/licencia.js emite una licencia Pro
 * gratis. Su unica barrera era acertar el email del dueño, y eso no alcanza:
 *   - el header x-mv-app que pide esta HARDCODEADO en landing/index.html, o sea
 *     a la vista de cualquiera con F12;
 *   - el usuario de GitHub del dueño es publico, asi que su gmail es una
 *     conjetura obvia.
 * Con esas dos cosas cualquiera se emitia una licencia Pro y dejaba de pagar el
 * producto. Se comprobo desde afuera, sin credenciales, que devolvia una clave.
 *
 * Ahora hace falta ademas OWNER_BUILD_TOKEN, que solo tienen Vercel y el
 * workflow. Este test fija las tres propiedades que no pueden perderse:
 *   1. que el token se exija,
 *   2. que FALLE CERRADO si no esta configurado (un deploy sin configurar no
 *      puede reabrir el agujero),
 *   3. que el workflow lo mande.
 *
 * Uso:   node test/verificar_licencia_dueno.mjs
 */
import fs from "node:fs";
import path from "node:path";

const RAIZ = path.join(import.meta.dirname, "..");
const LIC = fs.readFileSync(path.join(RAIZ, "api/licencia.js"), "utf8");
const WF = fs.readFileSync(
  path.join(RAIZ, ".github/workflows/windows-installer.yml"), "utf8");

let fallas = 0;
const ok = (m) => console.log("OK     " + m);
const falla = (m) => { fallas++; console.log("FALLA  " + m); };

// El bloque del camino ?dueno=1, hasta su return.
const i = LIC.indexOf('String(q.dueno || "") === "1"');
if (i < 0) {
  falla("no encontre el camino ?dueno=1 en api/licencia.js");
} else {
  const bloque = LIC.slice(i, LIC.indexOf("\n  }", i));

  // 1) exige el token del build
  if (/OWNER_BUILD_TOKEN/.test(bloque)) ok("el camino ?dueno=1 exige OWNER_BUILD_TOKEN");
  else falla("?dueno=1 NO exige OWNER_BUILD_TOKEN: cualquiera que adivine el email " +
             "se emite una licencia Pro gratis");

  // 2) falla cerrado: sin el token configurado, el camino se deshabilita.
  //    El "!buildToken" del if es lo que lo garantiza.
  if (/if\s*\(\s*!buildToken\s*\|\|/.test(bloque)) {
    ok("falla CERRADO: sin OWNER_BUILD_TOKEN configurado, el camino queda deshabilitado");
  } else {
    falla("sin el chequeo '!buildToken' un deploy sin la variable dejaria el " +
          "camino ABIERTO otra vez");
  }

  // 3) el token se compara, no solo se lee
  if (/enviado\s*!==\s*buildToken/.test(bloque)) ok("el token recibido se compara contra el configurado");
  else falla("el token no se compara: leerlo sin verificarlo no protege nada");

  // 4) el email sigue validandose (segunda barrera, no se perdio)
  if (/OWNER_EMAIL/.test(bloque) && /email\s*!==\s*ownerEmail/.test(bloque)) {
    ok("se mantiene la validacion por email exacto (segunda barrera)");
  } else falla("se perdio la validacion por OWNER_EMAIL");
}

// 5) el workflow manda el token
if (/x-mv-owner-build/.test(WF)) ok("el workflow manda el token en la cabecera");
else falla("el workflow no manda OWNER_BUILD_TOKEN: el build owner no podria pedir la licencia");
if (/OWNER_BUILD_TOKEN:\s*\$\{\{\s*secrets\.OWNER_BUILD_TOKEN\s*\}\}/.test(WF)) {
  ok("el token viaja desde un secret de GitHub, no hardcodeado");
} else falla("OWNER_BUILD_TOKEN deberia venir de secrets, no escrito en el workflow");

// 6) el token NUNCA puede estar escrito en el repo
const enRepo = /OWNER_BUILD_TOKEN\s*[:=]\s*["'][^"'$}]{6,}["']/.test(WF) ||
               /OWNER_BUILD_TOKEN\s*=\s*["'][^"'$]{6,}["']/.test(LIC);
if (enRepo) falla("hay un valor literal de OWNER_BUILD_TOKEN en el repo");
else ok("no hay ningun valor literal del token en el repo");

console.log("");
if (fallas) {
  console.error(`FALLO: ${fallas} problema(s) con la licencia de dueño.`);
  process.exit(1);
}
console.log("OK: la licencia de dueño solo se puede pedir desde el build de GitHub, "
  + "no desde la web, y falla cerrada si no esta configurada.");
