// api/checkout.js — Crea un pago para un plan, en MercadoPago (Checkout Pro,
// cobra en pesos uruguayos pese a mostrar USD) o PayPal (cobra USD real, sin
// conversion para el comprador — ver la aclaracion de moneda en la landing).
//
// El Access Token de MercadoPago vive SOLO en MP_ACCESS_TOKEN; las
// credenciales de PayPal en PAYPAL_CLIENT_ID/PAYPAL_CLIENT_SECRET (ver
// api/_paypal.js) — ninguna en el repo ni en el cliente. Si el procesador
// pedido no esta configurado, responde 503 y el boton avisa que el pago
// todavia no esta activo.
//
// Flujo MercadoPago: el boton "Comprar" hace POST aqui -> devolvemos
// init_point -> el cliente paga -> MP redirige a /gracias.html?payment_id=...
// -> gracias.html verifica el pago con /api/licencia y muestra la licencia.
//
// Flujo PayPal: mismo POST con {plan, proc:"paypal"} -> devolvemos el link
// de aprobacion de PayPal (mismo campo "init_point" para no bifurcar el
// cliente) -> el comprador aprueba en PayPal -> vuelve a
// /api/paypal-retorno, que cobra de verdad y redirige a
// /gracias.html?payment_id=...&proc=paypal.

import crypto from "crypto";
import { aplicarCors, clienteValido } from "./_seguridad.js";
import { crearOrden, paypalConfigurado } from "./_paypal.js";
import { guardarUtm } from "./_atribucion.js";

const PLANES = {
  starter: { titulo: "MV FBA IA — Starter (Celular)", precio: 29 },
  pro:     { titulo: "MV FBA IA — Pro (PC + Android)", precio: 129 },
  ia:      { titulo: "MV FBA IA — Pro IA (todo incluido)", precio: 34 },
};

export default async function handler(req, res) {
  aplicarCors(req, res, "POST, OPTIONS");
  if (req.method === "OPTIONS") return res.status(204).end();
  if (req.method !== "POST") return res.status(405).json({ error: "method" });
  if (!clienteValido(req)) return res.status(403).json({ error: "cliente_no_reconocido" });

  let body = req.body;
  if (typeof body === "string") { try { body = JSON.parse(body); } catch (e) { body = {}; } }
  body = body || {};
  const plan = PLANES[String(body.plan || "")];
  if (!plan) return res.status(400).json({ error: "plan_invalido" });

  const proto = (req.headers["x-forwarded-proto"] || "https").split(",")[0];
  const base = `${proto}://${req.headers.host}`;

  // cid: id de correlacion para atribucion de ventas (api/_atribucion.js) --
  // guarda el UTM que mando el cliente ANTES de salir a pagar, y ese mismo cid
  // viaja dentro del pago para poder releerlo cuando se confirme la compra.
  // Si el cliente no mando utm (o el almacen no esta configurado) esto es un
  // no-op silencioso: nunca bloquea el checkout.
  const cid = crypto.randomUUID();
  try { await guardarUtm(cid, body.utm); } catch (e) { /* almacen no configurado: no bloquea el pago */ }

  if (String(body.proc || "") === "paypal") {
    if (!paypalConfigurado()) return res.status(503).json({ error: "pago_no_configurado" });
    try {
      const { aprobarUrl } = await crearOrden({
        monto: plan.precio.toFixed(2),
        moneda: "USD",
        referencia: String(body.plan),
        returnUrl: `${base}/api/paypal-retorno`,
        cancelUrl: `${base}/#precios`,
        descripcion: plan.titulo,
        cid,
      });
      if (!aprobarUrl) return res.status(502).json({ error: "paypal_sin_link" });
      return res.status(200).json({ init_point: aprobarUrl });
    } catch (e) {
      return res.status(502).json({ error: "paypal_error", detail: String((e && e.message) || e) });
    }
  }

  const token = process.env.MP_ACCESS_TOKEN;
  if (!token) return res.status(503).json({ error: "pago_no_configurado" });

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
    metadata: { plan: String(body.plan), cid },
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
