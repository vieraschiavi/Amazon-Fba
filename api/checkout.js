// api/checkout.js — Crea un pago de MercadoPago (Checkout Pro) para un plan.
//
// El Access Token vive SOLO en la variable de entorno MP_ACCESS_TOKEN de Vercel
// (nunca en el repo ni en el cliente). Si no está configurada, responde 503 y el
// botón avisa que el pago todavía no está activo. Cobra en USD.
//
// Flujo: el botón "Comprar" hace POST aquí -> devolvemos init_point (URL de
// MercadoPago) -> el cliente paga -> MP redirige a /gracias.html?payment_id=...
// -> gracias.html verifica el pago con /api/licencia y muestra la licencia.

import { aplicarCors, clienteValido } from "./_seguridad.js";

const PLANES = {
  starter: { titulo: "MV Amazon FBA IA — Starter (Celular)", precio: 29 },
  pro:     { titulo: "MV Amazon FBA IA — Pro (PC + Android)", precio: 129 },
  ia:      { titulo: "MV Amazon FBA IA — Pro IA (todo incluido)", precio: 34 },
};

export default async function handler(req, res) {
  aplicarCors(req, res, "POST, OPTIONS");
  if (req.method === "OPTIONS") return res.status(204).end();
  if (req.method !== "POST") return res.status(405).json({ error: "method" });
  if (!clienteValido(req)) return res.status(403).json({ error: "cliente_no_reconocido" });

  const token = process.env.MP_ACCESS_TOKEN;
  if (!token) return res.status(503).json({ error: "pago_no_configurado" });

  let body = req.body;
  if (typeof body === "string") { try { body = JSON.parse(body); } catch (e) { body = {}; } }
  body = body || {};
  const plan = PLANES[String(body.plan || "")];
  if (!plan) return res.status(400).json({ error: "plan_invalido" });

  const proto = (req.headers["x-forwarded-proto"] || "https").split(",")[0];
  const base = `${proto}://${req.headers.host}`;

  const pref = {
    items: [{
      title: plan.titulo, quantity: 1, unit_price: plan.precio, currency_id: "USD",
    }],
    back_urls: {
      success: `${base}/gracias.html`,
      pending: `${base}/gracias.html`,
      failure: `${base}/#precios`,
    },
    auto_return: "approved",
    external_reference: String(body.plan),
    statement_descriptor: "MV FBA IA",
    metadata: { plan: String(body.plan) },
  };

  try {
    const r = await fetch("https://api.mercadopago.com/checkout/preferences", {
      method: "POST",
      headers: { "content-type": "application/json", authorization: `Bearer ${token}` },
      body: JSON.stringify(pref),
    });
    const d = await r.json();
    if (!r.ok) return res.status(502).json({ error: "mp_error", detail: d && d.message });
    return res.status(200).json({ init_point: d.init_point, id: d.id });
  } catch (e) {
    return res.status(502).json({ error: "fetch_fail" });
  }
}
