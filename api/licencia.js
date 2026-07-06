// api/licencia.js — Verifica un pago de MercadoPago y emite la licencia.
//
// La página /gracias.html llama aquí con el payment_id que devuelve MercadoPago.
// Verificamos SERVER-SIDE que el pago esté "approved" (con MP_ACCESS_TOKEN) y
// recién ahí generamos la clave de licencia — con la MISMA fórmula HMAC que usa
// la app para validarla (core/licencia.py y mobile/js/licencia.js). La licencia
// queda a nombre del email con el que el comprador pagó: ese mismo email va en
// la app para activarla.
import { aplicarCors, clienteValido } from "./_seguridad.js";
import { generarClave } from "./_licencia.js";
import { renovarPlanIA } from "./_cuotaia.js";

export default async function handler(req, res) {
  aplicarCors(req, res, "GET, OPTIONS");
  if (req.method === "OPTIONS") return res.status(204).end();
  // Defensa en profundidad: sin esto, un bot podria enumerar payment_id al
  // azar buscando pagos aprobados de OTRAS personas para pescar su email +
  // licencia. El header no detiene a un atacante dirigido, pero saca del
  // medio el escaneo automatico generico.
  if (!clienteValido(req)) return res.status(403).json({ error: "cliente_no_reconocido" });

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
    // Plan "Pro IA": cada pago aprobado extiende 30 dias de acceso a IA
    // incluida. No hay suscripcion automatica que "cancelar" -- si no vuelve
    // a pagar, el acceso vence solo (ver api/_cuotaia.js).
    if (plan === "ia" && email) {
      try { await renovarPlanIA(email); } catch (e) { /* almacen no configurado aun: no bloquea la licencia */ }
    }
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
