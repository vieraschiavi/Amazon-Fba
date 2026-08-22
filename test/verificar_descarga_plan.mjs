// © 2026 Martín Viera. Todos los derechos reservados.
/* verificar_descarga_plan.mjs — cada comprador baja SOLO lo que pago.
 *
 * POR QUE EXISTE
 * --------------
 * api/descarga.js validaba unicamente que el pago estuviera "approved", y el
 * ?tipo= (exe / bat / apk) lo elige quien llama, en la URL. O sea que con un
 * pago Starter de US$29 (celular) alcanzaba con sacar "&tipo=apk" del link
 * para bajarse el Pro de US$129 (PC), con el MISMO payment_id y sin tocar
 * nada mas. Y como los packs de creditos de IA tambien son pagos aprobados,
 * comprar creditos habilitaba bajarse el programa entero.
 *
 * No rompia nada ni dejaba error en ningun lado: simplemente se entregaba de
 * mas. Este test corre el handler DE VERDAD (con la API de pagos mockeada) y
 * fija la tabla de que incluye cada plan.
 *
 * Uso:   node test/verificar_descarga_plan.mjs
 */
process.env.KV_REST_API_URL = "PLACEHOLDER";
process.env.KV_REST_API_TOKEN = "test-token";
process.env.MP_ACCESS_TOKEN = "token-de-prueba";
// Sin token de GitHub a proposito: cuando el plan SI da derecho, el handler
// sigue hasta resolver el release y ahi corta con 502 (sin_token). Eso
// alcanza para distinguir "paso el control de plan" de "lo freno".
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

// Mock de la API de MercadoPago: devuelve un pago aprobado del plan pedido.
const fetchReal = globalThis.fetch;
function mockearPago(plan) {
  globalThis.fetch = async (url) => {
    if (String(url).includes("api.mercadopago.com")) {
      return {
        ok: true,
        json: async () => ({ status: "approved", external_reference: plan }),
      };
    }
    return fetchReal(url);
  };
}

// Cada caso usa una IP distinta: el limite es 30/hora por IP y no queremos
// que un caso haga fallar al siguiente por agotar cupo.
let n = 0;
async function pedir(plan, tipo) {
  mockearPago(plan);
  n += 1;
  const req = {
    headers: { "x-forwarded-for": `10.9.${Math.floor(n / 250)}.${n % 250}` },
    query: { payment_id: "PAGO-TEST", ...(tipo ? { tipo } : {}) },
  };
  const res = fakeRes();
  await handler(req, res);
  return res;
}

const NOMBRE = { "": "PC (.exe)", bat: "PC portable (.zip)", apk: "Android (APK)" };

// --- 1) Starter (US$29, celular): SOLO el APK ---
for (const tipo of ["", "bat"]) {
  const r = await pedir("starter", tipo);
  if (r._status === 403 && r._body && r._body.error === "plan_no_incluye") {
    ok(`Starter NO puede bajar ${NOMBRE[tipo]}`);
  } else {
    falla(`Starter (US$29) se bajo ${NOMBRE[tipo]} -> HTTP ${r._status} ` +
          `${JSON.stringify(r._body)} — es el Pro de US$129 regalado`);
  }
}
{
  const r = await pedir("starter", "apk");
  if (r._status !== 403) ok("Starter SI puede bajar Android (APK), que es lo que pago");
  else falla(`Starter no pudo bajar su propio APK -> ${JSON.stringify(r._body)}`);
}

// --- 2) Pro (US$129, PC + Android): las tres ---
for (const tipo of ["", "bat", "apk"]) {
  const r = await pedir("pro", tipo);
  if (r._status !== 403) ok(`Pro SI puede bajar ${NOMBRE[tipo]}`);
  else falla(`Pro (US$129) no pudo bajar ${NOMBRE[tipo]} -> ${JSON.stringify(r._body)}`);
}

// --- 3) Packs de creditos de IA: NINGUNA descarga ---
// Son pagos aprobados igual que una compra del programa, asi que sin la
// tabla de planes habilitaban cualquier descarga.
for (const tipo of ["", "bat", "apk"]) {
  const r = await pedir("creditos_chico", tipo);
  if (r._status === 403 && r._body && r._body.error === "plan_no_incluye") {
    ok(`un pack de CREDITOS no baja ${NOMBRE[tipo]}`);
  } else {
    falla(`un pack de creditos se bajo ${NOMBRE[tipo]} -> HTTP ${r._status}: ` +
          `comprar creditos no da derecho al programa`);
  }
}

// --- 4) un pago sin plan identificable no da derecho a nada ---
// Falla cerrado: ante la duda no se entrega, en vez de entregar de mas.
{
  const r = await pedir("", "");
  if (r._status === 403) ok("un pago sin plan identificable no baja nada (falla cerrado)");
  else falla(`un pago sin plan bajo el programa -> HTTP ${r._status}`);
}

globalThis.fetch = fetchReal;
await kv.cerrar?.();

console.log(fallas
  ? `\nFALLA: ${fallas} caso(s) — se esta entregando mas de lo que el cliente pago.`
  : "\nOK: cada plan baja exactamente lo suyo; los packs de creditos no bajan el programa.");
process.exit(fallas ? 1 : 0);
