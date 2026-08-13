// © 2026 Martín Viera. Todos los derechos reservados.
/* verificar_ventas_admin.mjs — api/ventas.js compara el secreto en tiempo
 * constante y limita intentos por IP.
 *
 * POR QUE EXISTE: "!==" corta apenas encuentra la primera diferencia
 * (filtracion de timing teorica) y no tenia ningun limite de velocidad para
 * probar valores de x-admin-secret. Bajo riesgo real (secreto de alta
 * entropia, la red real agrega ruido de por si), pero es una correccion
 * barata que cierra las dos cosas.
 *
 * Uso:   node test/verificar_ventas_admin.mjs
 */
process.env.KV_REST_API_URL = "PLACEHOLDER";
process.env.KV_REST_API_TOKEN = "test-token";
process.env.ADMIN_SECRET = "un-secreto-de-prueba-bien-largo-123456";
process.env.DB_PATH = "/tmp/verificar_ventas_admin_test.db";

import { iniciarMockKv } from "./mock_kv_servidor.mjs";

const kv = await iniciarMockKv();
process.env.KV_REST_API_URL = kv.url;

const { default: handler } = await import("../api/ventas.js");

let fallas = 0;
const ok = (m) => console.log("OK     " + m);
const falla = (m) => { fallas++; console.error("FALLA  " + m); };

function fakeRes() {
  const r = { _status: 200, _body: null };
  r.status = (s) => { r._status = s; return r; };
  r.json = (b) => { r._body = b; return r; };
  return r;
}
function fakeReq(ip, secreto) {
  return { method: "GET", headers: { "x-forwarded-for": ip, "x-admin-secret": secreto }, query: {} };
}

// --- secreto correcto pasa (aunque el almacen de ventas no este configurado
// de verdad, eso da 503 despues -- lo que importa es que NO sea 403) ---
{
  const res = fakeRes();
  await handler(fakeReq("203.0.113.10", process.env.ADMIN_SECRET), res);
  if (res._status !== 403) ok("el secreto correcto no se rechaza como no_autorizado");
  else falla("el secreto correcto se rechazo (403)");
}

// --- secreto incorrecto, incluso de la MISMA longitud, se rechaza ---
{
  const falso = "x".repeat(process.env.ADMIN_SECRET.length);
  const res = fakeRes();
  await handler(fakeReq("203.0.113.11", falso), res);
  if (res._status === 403) ok("un secreto falso de la MISMA longitud se rechaza");
  else falla("un secreto falso paso el chequeo");
}

// --- secreto de OTRA longitud tambien se rechaza (no revienta timingSafeEqual) ---
{
  const res = fakeRes();
  await handler(fakeReq("203.0.113.12", "corto"), res);
  if (res._status === 403) ok("un secreto de otra longitud se rechaza sin romper");
  else falla("un secreto de otra longitud no se rechazo con 403: " + res._status);
}

// --- limite por IP: 21 intentos fallidos seguidos de la misma IP, el 21 corta con 429 ---
{
  const IP = "203.0.113.13";
  let vistos429 = 0;
  for (let i = 0; i < 21; i++) {
    const res = fakeRes();
    await handler(fakeReq(IP, "nunca-es-el-correcto"), res);
    if (res._status === 429) vistos429++;
  }
  if (vistos429 === 1) ok("21 intentos seguidos de la misma IP: exactamente 1 se bloquea con 429");
  else falla(`se esperaba 1 bloqueo en 21 intentos, se vieron ${vistos429}`);
}

// --- comparacion en codigo fuente: no queda "!==" comparando el secreto ---
{
  const fs = await import("node:fs");
  const path = await import("node:path");
  const SRC = fs.readFileSync(path.join(import.meta.dirname, "..", "api/ventas.js"), "utf8");
  if (/timingSafeEqual/.test(SRC)) ok("ventas.js usa timingSafeEqual");
  else falla("ventas.js no usa timingSafeEqual");
  if (!/x-admin-secret["']\]\s*!==\s*secreto/.test(SRC))
    ok("  no quedo una comparacion directa \"!==\" del secreto");
  else falla("todavia queda una comparacion directa \"!==\" del secreto");
}

await kv.cerrar();

console.log("");
if (fallas) {
  console.error(`FALLO: ${fallas} problema(s) en api/ventas.js.`);
  process.exit(1);
}
console.log("OK: api/ventas.js compara el secreto en tiempo constante y limita intentos por IP.");
process.exit(0);
