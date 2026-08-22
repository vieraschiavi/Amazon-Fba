// © 2026 Martín Viera. Todos los derechos reservados.
// api/descarga.js — Descarga real del instalador de PC, la version portable
// sin instalador, y el APK Android.
//
// El repo es privado: el link "publico" de un Release de GitHub le da 404 a
// cualquier visitante anonimo (ver api/_release.js). Por eso esta funcion
// jamas redirige ahi directo -- resuelve el asset server-side y redirige al
// link firmado que da la API de GitHub, que ese si es descargable sin login.
//
// ?tipo= elige el asset dentro del release "pc-latest" (o android-latest):
//   (sin tipo)  instalador .exe (icono de Escritorio, Menu Inicio, desinstalador)
//   bat         version portable .zip sin instalador (para PCs que bloquean
//               ejecutar .exe -- se descomprime y se corre con INICIAR.bat)
//   apk         app Android
//
// ?demo=1 YA NO ENTREGA NADA (410): la demo dejo de ser una descarga abierta
// y pasa a ser 1:1 bajo pedido (ver api/demo-solicitud.js).
//
// Toda descarga exige DOS cosas, no una:
//   1. un pago aprobado real (MercadoPago o PayPal, via payment_id/orden
//      + ?proc=paypal si corresponde), y
//   2. que el PLAN de ese pago incluya lo que se esta pidiendo (ver INCLUYE).
// El punto 2 no existia: como el ?tipo= lo elige quien llama, un Starter de
// US$29 se convertia en el Pro de US$129 sacando "&tipo=apk" de la URL.
import { obtenerOrden, leerOrden, paypalConfigurado } from "./_paypal.js";
import { resolverDescargaRelease } from "./_release.js";
import { limitarPorIp } from "./_seguridad.js";

const RELEASE_PC = { tag: "pc-latest", asset: "MV_Amazon_FBA_IA_Setup.exe" };
const RELEASE_PC_BAT = { tag: "pc-latest", asset: "MV_FBA_IA_Portable.zip" };
const RELEASE_APK = { tag: "android-latest", asset: "MV-Amazon-FBA-IA.apk" };

function releasePedido(tipo) {
  if (tipo === "apk") return RELEASE_APK;
  if (tipo === "bat") return RELEASE_PC_BAT;
  return RELEASE_PC;
}

// QUE ENTREGA CADA PLAN
// ---------------------
// Un pago aprobado NO alcanza: hay que mirar QUE se compro. El "tipo" lo
// elige quien llama, en la URL, asi que sin esta tabla alcanzaba con sacar
// "&tipo=apk" para convertir un Starter de US$29 (celular) en el Pro de
// US$129 (PC), con el mismo payment_id y sin tocar nada mas. Peor todavia:
// los packs de CREDITOS de IA tambien son pagos aprobados, asi que comprar
// creditos habilitaba bajarse el programa entero.
//
// Las claves son los ids de PLANES en api/checkout.js, que es lo que viaja
// en external_reference (MercadoPago) y en reference_id (PayPal).
// Lo que no figura aca no da derecho a ninguna descarga -- incluidos los
// packs de recarga, a proposito.
const INCLUYE = {
  starter: ["apk"],                 // Starter (Celular)
  pro:     ["", "bat", "apk"],      // Pro (PC + Android); "" es el .exe
};

function planIncluye(plan, tipo) {
  const permitidos = INCLUYE[String(plan || "").trim().toLowerCase()];
  return Array.isArray(permitidos) && permitidos.includes(tipo);
}

// Respuesta comun para "pagaste, pero no esto". Se devuelve el plan y el tipo
// para que el propio comprador entienda que le falta (y para poder
// diagnosticar sin mirar logs). No expone nada: los dos valores ya los tiene
// quien hizo la compra.
function noIncluido(res, plan, tipo) {
  return res.status(403).json({
    error: "plan_no_incluye",
    plan: String(plan || ""),
    tipo: tipo || "exe",
    mensaje: "Tu plan no incluye esta version. Escribinos a vieraschiavi@gmail.com si crees que es un error.",
  });
}

async function redirigirA(release, res) {
  const r = await resolverDescargaRelease(release.tag, release.asset);
  // "motivo"/"status" nunca exponen el token -- son solo para diagnosticar
  // desde afuera (sin_token / release_no_encontrado / asset_no_encontrado /
  // sin_redirect) sin tener que mirar logs de Vercel.
  if (!r.url) return res.status(502).json({ error: "descarga_no_disponible", motivo: r.motivo, status: r.status });
  res.setHeader("Location", r.url);
  return res.status(302).end();
}

export default async function handler(req, res) {
  // A diferencia del resto de api/*.js, ESTE endpoint se llega con un <a
  // href> normal (navegacion de pagina completa, ver landing/index.html y
  // gracias.html) -- no con fetch() desde el JS del sitio. Un navegador NO
  // manda headers custom en una navegacion asi, asi que clienteValido()
  // (que exige el header x-mv-app) rompería la descarga real: por eso ese
  // chequeo no aplica aca, y el unico freno posible es el limite por IP.
  //
  // Antes este endpoint era el UNICO de todo api/* sin ningun limite: cada
  // llamada exitosa gasta 2 requests contra la API de GitHub con el token
  // COMPARTIDO de todos los clientes (GITHUB_RELEASE_TOKEN, 5000/hora). Un
  // script anonimo en loop contra ?demo=1 (que ademas no exige pago) agotaba
  // ese cupo en minutos -- y a partir de ahi, la descarga de un cliente que
  // acaba de pagar de verdad tambien fallaba, durante el resto de la hora.
  const limite = await limitarPorIp(req, "descarga", 30, 3600);
  if (!limite.permitido) return res.status(429).json({ error: "demasiados_intentos" });

  const q = req.query || {};
  const tipo = String(q.tipo || "");
  const release = releasePedido(tipo);

  // La demo ABIERTA se dio de baja a proposito. Antes esta rama entregaba el
  // .exe y el .zip COMPLETOS a cualquiera que abriera la URL: sin pago, sin
  // dejar rastro de quien se los llevaba, y con el motor de negocio adentro.
  // Era el activo de ingenieria regalado a la competencia.
  //
  // Ahora la demo se pide (formulario -> mail al dueño), se agenda y se
  // muestra en vivo: ver api/demo-solicitud.js y la seccion #solicitar-demo
  // de la landing. 410 y no 404 a proposito: el recurso EXISTIO y ya no, que
  // es exactamente lo que pasa -- y asi un link viejo compartido por ahi no
  // parece un error del sitio.
  if (String(q.demo || "") === "1") {
    return res.status(410).json({
      error: "demo_bajo_pedido",
      mensaje: "La demo ahora es 1:1 y se pide desde mvfbaia.com/#solicitar-demo",
    });
  }

  const paymentId = q.payment_id || q.collection_id;
  if (!paymentId) return res.status(400).json({ error: "sin_pago" });

  if (String(q.proc || "") === "paypal") {
    if (!paypalConfigurado()) return res.status(503).json({ error: "pago_no_configurado" });
    try {
      const orden = await obtenerOrden(paymentId);
      const { completado, estado, plan } = leerOrden(orden);
      if (!completado) return res.status(403).json({ error: "no_pagado", estado });
      if (!planIncluye(plan, tipo)) return noIncluido(res, plan, tipo);
      return redirigirA(release, res);
    } catch (e) {
      return res.status(502).json({ error: "paypal_error" });
    }
  }

  const token = process.env.MP_ACCESS_TOKEN;
  if (!token) return res.status(503).json({ error: "pago_no_configurado" });

  try {
    const r = await fetch(`https://api.mercadopago.com/v1/payments/${encodeURIComponent(paymentId)}`, {
      headers: { authorization: `Bearer ${token}` },
    });
    const p = await r.json();
    if (!r.ok) return res.status(502).json({ error: "mp_error" });
    if (p.status !== "approved") return res.status(403).json({ error: "no_pagado", estado: p.status });
    // Mismo origen que usa api/licencia.js para leer el plan del pago.
    const plan = p.external_reference || (p.metadata && p.metadata.plan) || "";
    if (!planIncluye(plan, tipo)) return noIncluido(res, plan, tipo);
    return redirigirA(release, res);
  } catch (e) {
    return res.status(502).json({ error: "fetch_fail" });
  }
}
