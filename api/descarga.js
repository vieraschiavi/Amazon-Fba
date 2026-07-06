// api/descarga.js — Descarga del instalador de PC, SOLO para quien pagó
// (MercadoPago o PayPal).
//
// gracias.html llama aquí con el payment_id/orden y, si corresponde,
// ?proc=paypal. Verificamos server-side que el pago esté aprobado y recién
// ahí redirigimos al instalador publicado como Release de GitHub. Sin
// pago -> 403.
//
// Nota honesta: la URL final del Release es pública; el gate evita que se
// muestre el link sin pagar, pero para un bloqueo total habría que servir el
// binario desde almacenamiento privado con URL firmada (mejora futura).
import { obtenerOrden, leerOrden, paypalConfigurado } from "./_paypal.js";

const INSTALADOR_PC =
  "https://github.com/vieraschiavi/Amazon-Fba/releases/download/pc-latest/MV_Amazon_FBA_IA_Setup.exe";

export default async function handler(req, res) {
  const q = req.query || {};
  const paymentId = q.payment_id || q.collection_id;
  if (!paymentId) return res.status(400).json({ error: "sin_pago" });

  if (String(q.proc || "") === "paypal") {
    if (!paypalConfigurado()) return res.status(503).json({ error: "pago_no_configurado" });
    try {
      const orden = await obtenerOrden(paymentId);
      const { completado, estado } = leerOrden(orden);
      if (!completado) return res.status(403).json({ error: "no_pagado", estado });
      res.setHeader("Location", INSTALADOR_PC);
      return res.status(302).end();
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
    res.setHeader("Location", INSTALADOR_PC);
    return res.status(302).end();
  } catch (e) {
    return res.status(502).json({ error: "fetch_fail" });
  }
}
