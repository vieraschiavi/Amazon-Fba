// api/licencia.js — Verifica un pago de MercadoPago y emite la licencia.
//
// La página /gracias.html llama aquí con el payment_id que devuelve MercadoPago.
// Verificamos SERVER-SIDE que el pago esté "approved" (con MP_ACCESS_TOKEN) y
// recién ahí generamos la clave de licencia — con la MISMA fórmula HMAC que usa
// la app para validarla (core/licencia.py y mobile/js/licencia.js). La licencia
// queda a nombre del email con el que el comprador pagó: ese mismo email va en
// la app para activarla.
import crypto from "crypto";

const SECRETO = process.env.LICENCIA_SECRETO || "mv-amazon-fba-2026-clave-de-firma";
const DOMINIO = "MV-Amazon-Fba";

function generarClave(email) {
  const base = String(email || "").trim().toLowerCase() + DOMINIO;
  const hex = crypto.createHmac("sha256", SECRETO).update(base).digest("hex").toUpperCase().slice(0, 16);
  return "MVFBA-" + [hex.slice(0, 4), hex.slice(4, 8), hex.slice(8, 12), hex.slice(12, 16)].join("-");
}

export default async function handler(req, res) {
  res.setHeader("Access-Control-Allow-Origin", "*");
  if (req.method === "OPTIONS") return res.status(204).end();

  const token = process.env.MP_ACCESS_TOKEN;
  if (!token) return res.status(503).json({ error: "pago_no_configurado" });

  const q = req.query || {};
  const paymentId = q.payment_id || q.collection_id || q.paymentId;
  if (!paymentId) return res.status(400).json({ error: "sin_pago" });

  try {
    const r = await fetch(`https://api.mercadopago.com/v1/payments/${encodeURIComponent(paymentId)}`, {
      headers: { authorization: `Bearer ${token}` },
    });
    const p = await r.json();
    if (!r.ok) return res.status(502).json({ error: "mp_error" });
    if (p.status !== "approved") {
      return res.status(200).json({ aprobado: false, estado: p.status });
    }
    const email = (p.payer && p.payer.email) || "";
    const plan = p.external_reference || (p.metadata && p.metadata.plan) || "";
    return res.status(200).json({
      aprobado: true,
      plan,
      email,
      licencia: generarClave(email),
    });
  } catch (e) {
    return res.status(502).json({ error: "fetch_fail" });
  }
}
