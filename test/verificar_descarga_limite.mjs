// © 2026 Martín Viera. Todos los derechos reservados.
/* verificar_descarga_limite.mjs — api/descarga.js tiene limite por IP.
 *
 * POR QUE EXISTE: era el UNICO endpoint de todo api/* sin ninguna de las
 * protecciones que el resto ya tiene (ver api/_seguridad.js). Cada llamada
 * exitosa gasta 2 requests contra la API de GitHub con el token COMPARTIDO
 * de TODOS los clientes (GITHUB_RELEASE_TOKEN, 5000/hora) -- y ?demo=1 ni
 * siquiera exige pago. Un script anonimo en loop agotaba ese cupo en
 * minutos, y a partir de ahi la descarga de un cliente que acaba de pagar
 * de verdad tambien fallaba, durante el resto de la hora.
 *
 * clienteValido() (el header x-mv-app) NO se agrego aca a proposito: este
 * endpoint se llega con un <a href> normal (navegacion de pagina completa,
 * ver landing/index.html), no con fetch() desde el JS del sitio -- un
 * navegador no manda headers custom en una navegacion asi, asi que exigir
 * ese header rompería la descarga real. El unico freno aplicable es
 * limitarPorIp, y es lo que este test fija.
 *
 * Uso:   node test/verificar_descarga_limite.mjs
 */
process.env.KV_REST_API_URL = "PLACEHOLDER";
process.env.KV_REST_API_TOKEN = "test-token";
// Sin token real de GitHub: las llamadas que SI pasan el limite van a fallar
// resolviendo el release (502/503), pero eso pasa DESPUES del chequeo de
// limite -- no hace falta un token real para probar que el limite corta.
delete process.env.GITHUB_RELEASE_TOKEN;

import { iniciarMockKv } from "./mock_kv_servidor.mjs";

const kv = await iniciarMockKv();
process.env.KV_REST_API_URL = kv.url;

const { default: handler } = await import("../api/descarga.js");

let fallas = 0;
const ok = (m) => console.log("OK     " + m);
const falla = (m) => { fallas++; console.error("FALLA  " + m); };

function fakeRes() {
  const r = { _status: 200, _body: null, _headers: {} };
  r.status = (s) => { r._status = s; return r; };
  r.json = (b) => { r._body = b; return r; };
  r.end = () => r;
  r.setHeader = (k, v) => { r._headers[k] = v; };
  return r;
}
function fakeReq(ip, query) {
  return { headers: { "x-forwarded-for": ip }, query };
}

// --- 30 requests de la MISMA ip: las primeras 30 pasan el limite (pueden
// fallar despues por falta de token de GitHub, eso es otro problema), la 31
// tiene que cortar ANTES, con 429 ---
const IP = "203.0.113.50";
let vistos429 = 0, primerNo429Index = -1;
for (let i = 0; i < 31; i++) {
  const res = fakeRes();
  await handler(fakeReq(IP, { demo: "1" }), res);
  if (res._status === 429) vistos429++;
  else if (primerNo429Index === -1) primerNo429Index = i;
}
if (vistos429 === 1) ok("de 31 requests seguidas de la misma IP, exactamente 1 se bloquea con 429");
else falla(`se esperaba exactamente 1 bloqueo en 31 requests, se vieron ${vistos429}`);

// --- otra IP arranca con su propio cupo, no hereda el bloqueo ajeno ---
{
  const res = fakeRes();
  await handler(fakeReq("198.51.100.7", { demo: "1" }), res);
  if (res._status !== 429) ok("una IP distinta no esta bloqueada por el cupo agotado de la primera");
  else falla("una IP nueva llego bloqueada -- el limite no deberia ser global");
}

// --- el limite corre ANTES de intentar resolver el release (no gasta la
// llamada a GitHub si ya esta bloqueado) ---
{
  const res = fakeRes();
  await handler(fakeReq(IP, { demo: "1" }), res);   // esta IP ya agoto su cupo arriba
  if (res._status === 429 && res._body && res._body.error === "demasiados_intentos")
    ok("el bloqueo llega ANTES de tocar la resolucion del release (respuesta clara, no un 502 generico)");
  else falla("el bloqueo no llego con el mensaje esperado: " + JSON.stringify(res._body));
}

// --- clienteValido() NO se exige (romperia la navegacion real por <a href>) ---
{
  const fs = await import("node:fs");
  const path = await import("node:path");
  const SRC = fs.readFileSync(path.join(import.meta.dirname, "..", "api/descarga.js"), "utf8");
  // Se descartan las lineas de COMENTARIO antes de buscar: clienteValido
  // puede nombrarse ahi explicando por que no se usa (como en este mismo
  // archivo); lo que no puede pasar es que se IMPORTE o se LLAME de verdad.
  const codigo = SRC.split("\n").filter((l) => !l.trim().startsWith("//")).join("\n");
  if (!/clienteValido\s*\(|import\s*\{[^}]*clienteValido/.test(codigo))
    ok("descarga.js no exige clienteValido (se llega por navegacion, no por fetch)");
  else falla("descarga.js exige clienteValido -- eso rompe la descarga real via <a href>");
  if (/limitarPorIp/.test(SRC)) ok("descarga.js usa limitarPorIp");
  else falla("descarga.js no usa limitarPorIp");
}

await kv.cerrar();

console.log("");
if (fallas) {
  console.error(`FALLO: ${fallas} problema(s) en el limite de api/descarga.js.`);
  process.exit(1);
}
console.log("OK: api/descarga.js limita por IP sin romper la descarga real via <a href>.");
process.exit(0);
