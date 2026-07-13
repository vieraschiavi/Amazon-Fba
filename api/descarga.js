// api/descarga.js — Descarga real del instalador de PC y del APK Android.
//
// El repo es privado: el link "publico" de un Release de GitHub le da 404 a
// cualquier visitante anonimo (ver api/_release.js). Por eso esta funcion
// jamas redirige ahi directo -- resuelve el asset server-side y redirige al
// link firmado que da la API de GitHub, que ese si es descargable sin login.
//
// ?demo=1: instalador de PC SIN pago (el limite de 3 dias lo controla la
// propia app al abrirla, no la descarga) -- lo usan los botones "Probar
// demo" de la landing.
// Sin ?demo: exige un pago aprobado real (MercadoPago o PayPal, via
// payment_id/orden + ?proc=paypal si corresponde). gracias.html llama aca
// para el instalador de PC y, con ?tipo=apk, para el APK de Android -- la
// misma licencia sirve para ambos, no hay gate distinto por plan.
import { obtenerOrden, leerOrden, paypalConfigurado } from "./_paypal.js";
import { resolverDescargaRelease } from "./_release.js";

const RELEASE_PC = { tag: "pc-latest", asset: "MV_Amazon_FBA_IA_Setup.exe" };
const RELEASE_APK = { tag: "android-latest", asset: "MV-Amazon-FBA-IA.apk" };

async function redirigirA(release, res) {
  const url = await resolverDescargaRelease(release.tag, release.asset);
  if (!url) return res.status(502).json({ error: "descarga_no_disponible" });
  res.setHeader("Location", url);
  return res.status(302).end();
}

export default async function handler(req, res) {
  const q = req.query || {};
  const release = String(q.tipo || "") === "apk" ? RELEASE_APK : RELEASE_PC;

  if (String(q.demo || "") === "1") return redirigirA(RELEASE_PC, res);

  const paymentId = q.payment_id || q.collection_id;
  if (!paymentId) return res.status(400).json({ error: "sin_pago" });

  if (String(q.proc || "") === "paypal") {
    if (!paypalConfigurado()) return res.status(503).json({ error: "pago_no_configurado" });
    try {
      const orden = await obtenerOrden(paymentId);
      const { completado, estado } = leerOrden(orden);
      if (!completado) return res.status(403).json({ error: "no_pagado", estado });
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
    return redirigirA(release, res);
  } catch (e) {
    return res.status(502).json({ error: "fetch_fail" });
  }
}
