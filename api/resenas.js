// api/resenas.js — Reseñas de compradores para la landing (puntaje + texto).
//
// GET es publico (sin licencia ni header de app): la landing la llama para
// mostrarla a CUALQUIER visitante antes de que compre, asi que no puede
// exigir credenciales de cliente.
//
// POST exige un payment_id REAL, verificado server-side contra MercadoPago o
// PayPal (mismo criterio que api/reembolso.js) -- nunca se confia en el
// plan/email que mande el cliente. Una reseña por pago (api/_resenas.js es
// idempotente por payment_id), asi nadie infla el promedio repitiendo envios.
import { aplicarCors, clienteValido } from "./_seguridad.js";
import { obtenerOrden, leerOrden, paypalConfigurado } from "./_paypal.js";
import { agregarResenaSiNueva, listarResenas, resumenResenas } from "./_resenas.js";

export default async function handler(req, res) {
  aplicarCors(req, res, "GET, POST, OPTIONS");
  if (req.method === "OPTIONS") return res.status(204).end();

  if (req.method === "GET") {
    const q = req.query || {};
    const cantidad = Math.min(50, Math.max(1, parseInt(q.n, 10) || 20));
    const [items, resumen] = await Promise.all([listarResenas(cantidad), resumenResenas()]);
    return res.status(200).json({ items, resumen });
  }

  if (req.method !== "POST") return res.status(405).json({ error: "method" });
  if (!clienteValido(req)) return res.status(403).json({ error: "cliente_no_reconocido" });

  let body = req.body;
  if (typeof body === "string") { try { body = JSON.parse(body); } catch (e) { body = {}; } }
  body = body || {};
  const paymentId = String(body.payment_id || "").trim();
  const puntaje = parseInt(body.puntaje, 10);
  const comentario = String(body.comentario || "").trim().slice(0, 600);
  const nombre = String(body.nombre || "").trim().slice(0, 40) || "Cliente verificado";
  if (!paymentId) return res.status(400).json({ error: "sin_pago" });
  if (!(puntaje >= 1 && puntaje <= 5)) return res.status(400).json({ error: "puntaje_invalido" });
  if (comentario.length < 8) return res.status(400).json({ error: "comentario_muy_corto" });

  let plan = "";
  if (String(body.proc || "") === "paypal") {
    if (!paypalConfigurado()) return res.status(503).json({ error: "pago_no_configurado" });
    try {
      const orden = await obtenerOrden(paymentId);
      const { completado, plan: p } = leerOrden(orden);
      if (!completado) return res.status(400).json({ error: "no_aprobado" });
      plan = p || "";
    } catch (e) {
      return res.status(502).json({ error: "paypal_error" });
    }
  } else {
    const token = process.env.MP_ACCESS_TOKEN;
    if (!token) return res.status(503).json({ error: "pago_no_configurado" });
    try {
      const r = await fetch(`https://api.mercadopago.com/v1/payments/${encodeURIComponent(paymentId)}`, {
        headers: { authorization: `Bearer ${token}` },
      });
      const p = await r.json();
      if (!r.ok) return res.status(502).json({ error: "mp_error" });
      if (p.status !== "approved") return res.status(400).json({ error: "no_aprobado", estado: p.status });
      plan = p.external_reference || (p.metadata && p.metadata.plan) || "";
    } catch (e) {
      return res.status(502).json({ error: "fetch_fail" });
    }
  }

  const guardada = await agregarResenaSiNueva({ paymentId, nombre, puntaje, comentario, plan });
  if (!guardada) return res.status(409).json({ error: "ya_reseniado" });
  return res.status(200).json({ ok: true });
}
