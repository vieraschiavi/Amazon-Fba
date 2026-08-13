// © 2026 Martín Viera. Todos los derechos reservados.
/* verificar_limite_endpoints_pago.mjs — reembolso.js, checkout.js y
 * resenas.js tienen limitarPorIp, igual que licencia.js/ia.js/mercado.js.
 *
 * POR QUE EXISTE: de los endpoints que exigen clienteValido, estos tres eran
 * los unicos SIN limite por IP (confirmado por grep contra el resto de
 * api/*.js). reembolso.js mueve plata real y distingue motivos de rechazo
 * (no_aprobado/email_no_coincide/fuera_de_plazo/ya_reembolsado) que sirven
 * de oraculo para enumerar payment_id o emails candidatos sin fricción.
 * checkout.js crea ordenes reales en PayPal/MercadoPago con las credenciales
 * del comercio -- sin limite, se puede generar spam de ordenes vacias y
 * activar los sistemas antifraude de esas cuentas. resenas.js (POST) permite
 * el mismo tipo de enumeracion de payment_id, con menor impacto.
 *
 * verificar_seguridad.mjs ya prueba limitarPorIp() en si misma (aislamiento
 * entre IPs, entre prefijos, el tope). Este test fija especificamente que
 * estos TRES endpoints la llamen, con el chequeo ANTES de tocar el
 * procesador de pagos real.
 *
 * Uso:   node test/verificar_limite_endpoints_pago.mjs
 */
import fs from "node:fs";
import path from "node:path";

const RAIZ = path.join(import.meta.dirname, "..");
let fallas = 0;
const ok = (m) => console.log("OK     " + m);
const falla = (m) => { fallas++; console.error("FALLA  " + m); };

for (const archivo of ["api/reembolso.js", "api/checkout.js", "api/resenas.js"]) {
  const src = fs.readFileSync(path.join(RAIZ, archivo), "utf8");
  const codigo = src.split("\n").filter((l) => !l.trim().startsWith("//")).join("\n");

  if (/limitarPorIp\s*}\s*from\s*["']\.\/_seguridad\.js["']|limitarPorIp\s*,/.test(codigo) &&
      /import\s*\{[^}]*limitarPorIp[^}]*\}\s*from\s*["']\.\/_seguridad\.js["']/.test(codigo))
    ok(`${archivo} importa limitarPorIp`);
  else falla(`${archivo} no importa limitarPorIp`);

  const llamada = /await\s+limitarPorIp\(req,\s*["'][^"']+["']/.exec(codigo);
  if (llamada) ok(`  ${archivo} lo llama con un prefijo propio (${llamada[0].match(/["']([^"']+)["']/)[1]})`);
  else falla(`${archivo} no llama a limitarPorIp(req, ...)`);

  if (/if\s*\(!limite\.permitido\)\s*return\s+res\.status\(429\)/.test(codigo))
    ok(`  ${archivo} corta con 429 si el limite no lo permite`);
  else falla(`${archivo} no corta con 429 cuando el limite lo rechaza`);

  // el chequeo tiene que estar ANTES de tocar el procesador de pagos real
  // (fetch a mercadopago.com / paypal, o crearOrden/obtenerOrden/reembolsarCaptura)
  const idxLimite = codigo.indexOf("limitarPorIp(req,");
  const idxPago = Math.min(
    ...["crearOrden(", "obtenerOrden(", "reembolsarCaptura(", "mercadopago.com"]
      .map((s) => { const i = codigo.indexOf(s); return i === -1 ? Infinity : i; })
  );
  if (idxLimite !== -1 && idxPago !== Infinity && idxLimite < idxPago)
    ok(`  ${archivo}: el limite corre ANTES de tocar el procesador de pagos`);
  else falla(`${archivo}: no se pudo confirmar que el limite corra antes del pago`);
}

console.log("");
if (fallas) {
  console.error(`FALLO: ${fallas} problema(s) en el limite por IP de los endpoints de pago.`);
  process.exit(1);
}
console.log("OK: reembolso.js, checkout.js y resenas.js limitan por IP antes de tocar el procesador de pagos.");
