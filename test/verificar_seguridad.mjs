// © 2026 Martín Viera. Todos los derechos reservados.
/* verificar_seguridad.mjs — Test de regresion de api/_seguridad.js
 * (limitarPorIp, ipDeRequest) contra un servidor KV real (mock_kv_servidor.mjs
 * emula la API REST de Upstash, no mockea el codigo propio).
 *
 * Motiva este test un bug real encontrado en la auditoria: api/ia.js contaba
 * las preguntas anonimas por "dispositivo || email", y si un script mandaba
 * los dos vacios, revisarAnonimo() devolvia "permitido, sin contar" -- Claude
 * gratis e ilimitado a costa de la clave del dueño. El mismo patron (sin
 * limite alguno) existia en api/mercado.js (Keepa) y api/licencia.js
 * (permitia enumerar payment_id ajenos sin ningun freno de intentos).
 * limitarPorIp() es el arreglo compartido por los tres.
 *
 * Uso:   node test/verificar_seguridad.mjs
 */
process.env.KV_REST_API_URL = "PLACEHOLDER"; // se pisa abajo, antes del primer import real
process.env.KV_REST_API_TOKEN = "test-token";

import { iniciarMockKv } from "./mock_kv_servidor.mjs";

const kv = await iniciarMockKv();
process.env.KV_REST_API_URL = kv.url; // _almacen.js lee esto UNA vez al importarse

const { limitarPorIp, ipDeRequest } = await import("../api/_seguridad.js");
const { almacenConfigurado } = await import("../api/_almacen.js");

let fallas = 0;
function assert(cond, msg) {
  if (!cond) { console.error("FALLA  " + msg); fallas++; }
  else console.log("OK     " + msg);
}

assert(almacenConfigurado(), "el mock de KV queda configurado (BASE/TOKEN detectados)");

function reqCon(ip) {
  return { headers: { "x-forwarded-for": ip } };
}

// --- ipDeRequest ---
assert(ipDeRequest(reqCon("203.0.113.9")) === "203.0.113.9", "ipDeRequest toma la primera IP de x-forwarded-for");
assert(ipDeRequest(reqCon("203.0.113.9, 10.0.0.1")) === "203.0.113.9",
  "ipDeRequest ignora los proxies intermedios (se queda con la primera)");
assert(ipDeRequest({ headers: {}, socket: {} }) === "desconocida",
  "ipDeRequest no rompe si no hay ni x-forwarded-for ni socket.remoteAddress");

// --- limitarPorIp: el caso central, tope=3 en una IP ---
{
  const req = reqCon("198.51.100.1");
  const r1 = await limitarPorIp(req, "test", 3, 3600);
  const r2 = await limitarPorIp(req, "test", 3, 3600);
  const r3 = await limitarPorIp(req, "test", 3, 3600);
  const r4 = await limitarPorIp(req, "test", 3, 3600);
  assert(r1.permitido && r2.permitido && r3.permitido, "los primeros 3 intentos de una IP se permiten");
  assert(r4.permitido === false, "el 4to intento de la MISMA IP en la MISMA ventana se bloquea");
}

// --- otra IP no comparte el cupo (el limite es POR ip) ---
{
  const otraIp = reqCon("198.51.100.2");
  const r = await limitarPorIp(otraIp, "test", 3, 3600);
  assert(r.permitido === true, "una IP distinta arranca con su propio cupo, no hereda el bloqueo ajeno");
}

// --- prefijos distintos no se mezclan (mercado vs licencia vs ia comparten backend) ---
{
  const req = reqCon("198.51.100.3");
  await limitarPorIp(req, "prefijoA", 1, 3600); // agota el cupo de prefijoA para esta IP
  const bloqueadoA = await limitarPorIp(req, "prefijoA", 1, 3600);
  const libreB = await limitarPorIp(req, "prefijoB", 1, 3600);
  assert(bloqueadoA.permitido === false, "prefijoA queda bloqueado tras agotar su propio cupo");
  assert(libreB.permitido === true, "prefijoB (otro endpoint) no se ve afectado por el cupo de prefijoA");
}

// --- reproduccion del bug real: id vacio ya NO da "permitido sin contar" ---
// (revisarAnonimo de api/ia.js no se exporta; lo que se prueba aca es que la
// pieza que soluciona el bug -- contar por IP en vez de saltear el conteo --
// funciona con normalidad para cualquier IP, incluida la que tendria un
// request con dispositivo/email vacios.)
{
  const atacante = reqCon("192.0.2.50");
  let ultimaPermitida = true;
  for (let i = 0; i < 31; i++) {
    const r = await limitarPorIp(atacante, "ia-repro", 30, 3600);
    ultimaPermitida = r.permitido;
  }
  assert(ultimaPermitida === false,
    "31 requests seguidos de la MISMA ip contra un tope de 30 terminan bloqueados (antes: ilimitado)");
}

await kv.cerrar();

if (fallas) {
  console.error(`\n${fallas} falla(s) en _seguridad.js.`);
  process.exit(1);
} else {
  console.log(`\nOK: limitarPorIp()/ipDeRequest() cubren el tope por IP, el aislamiento entre IPs y entre prefijos.`);
  process.exit(0);
}
