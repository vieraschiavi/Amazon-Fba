// api/reembolso.js — Reembolso AUTOMATICO de la garantia de 7 dias, via
// MercadoPago o PayPal segun como se pago.
//
// Mueve plata real: todo se valida SERVER-SIDE contra el procesador
// correspondiente, nunca contra lo que mande el cliente. Tres condiciones,
// las tres obligatorias:
//   1) El pago existe y esta aprobado/completado.
//   2) El email que manda el visitante coincide con el email real del pagador
//      (evita que alguien reembolse el pago de otra persona adivinando un
//      payment_id — el mismo riesgo de enumeracion que ya se mitigo en
//      api/licencia.js, pero aca con plata de por medio, asi que se re-valida).
//   3) Estan dentro de los 7 dias desde que el pago se aprobo/capturo (regla
//      de negocio real, no solo texto de marketing).
//
// Recien si las tres se cumplen se llama al refund real (MercadoPago:
// POST /v1/payments/{id}/refunds; PayPal: POST /v2/payments/captures/{id}/refund
// via api/_paypal.js).
//
// Ademas de devolver la plata, revoca la licencia (api/_revocacion.js): sin
// esto alguien podia reembolsar y seguir usando la app para siempre, porque
// el HMAC de la licencia no sabe que el pago se devolvio. Requiere el mismo
// almacen (Vercel KV/Upstash) que ya usa la cuota de IA -- si no esta
// configurado, el reembolso igual se procesa (la plata se devuelve siempre),
// simplemente no queda revocada la licencia.
import { aplicarCors, clienteValido } from "./_seguridad.js";
import { obtenerOrden, leerOrden, reembolsarCaptura, paypalConfigurado } from "./_paypal.js";
import { revocarLicencia } from "./_revocacion.js";

const VENTANA_DIAS = 7;

export default async function handler(req, res) {
  aplicarCors(req, res, "POST, OPTIONS");
  if (req.method === "OPTIONS") return res.status(204).end();
  if (req.method !== "POST") return res.status(405).json({ error: "method" });
  if (!clienteValido(req)) return res.status(403).json({ error: "cliente_no_reconocido" });

  let body = req.body;
  if (typeof body === "string") { try { body = JSON.parse(body); } catch (e) { body = {}; } }
  body = body || {};
  const paymentId = String(body.payment_id || "").trim();
  const email = String(body.email || "").trim().toLowerCase();
  if (!paymentId || !email) return res.status(400).json({ error: "faltan_datos" });

  if (String(body.proc || "") === "paypal") {
    if (!paypalConfigurado()) return res.status(503).json({ error: "pago_no_configurado" });
    try {
      const orden = await obtenerOrden(paymentId);
      const { email: emailPago, completado, captura } = leerOrden(orden);
      if (!completado || !captura) return res.status(400).json({ error: "no_aprobado" });
      if (!emailPago || emailPago.toLowerCase() !== email) {
        return res.status(403).json({ error: "email_no_coincide" });
      }
      if (captura.reembolsada) return res.status(409).json({ error: "ya_reembolsado" });
      const fechaCaptura = captura.creada ? new Date(captura.creada).getTime() : null;
      if (!fechaCaptura || Number.isNaN(fechaCaptura)) {
        return res.status(502).json({ error: "sin_fecha_aprobacion" });
      }
      const dias = (Date.now() - fechaCaptura) / 86400000;
      if (dias > VENTANA_DIAS) return res.status(403).json({ error: "fuera_de_plazo", dias: Math.floor(dias) });

      await reembolsarCaptura(captura.id);
      try { await revocarLicencia(email); } catch (e) { /* almacen no configurado: la plata igual se devolvio */ }
      return res.status(200).json({
        ok: true,
        mensaje: "Reembolso procesado. Puede tardar unos días en verse reflejado según tu medio de pago.",
      });
    } catch (e) {
      return res.status(502).json({ error: "paypal_error", detalle: String((e && e.message) || e) });
    }
  }

  const token = process.env.MP_ACCESS_TOKEN;
  if (!token) return res.status(503).json({ error: "pago_no_configurado" });

  try {
    // 1) Traer el pago real desde MercadoPago (nunca confiar en el cliente).
    const r = await fetch(`https://api.mercadopago.com/v1/payments/${encodeURIComponent(paymentId)}`, {
      headers: { authorization: `Bearer ${token}` },
    });
    const p = await r.json();
    if (!r.ok) return res.status(502).json({ error: "mp_error" });

    if (p.status !== "approved") {
      return res.status(400).json({ error: "no_aprobado", estado: p.status });
    }
    const emailPago = String((p.payer && p.payer.email) || "").trim().toLowerCase();
    if (!emailPago || emailPago !== email) {
      return res.status(403).json({ error: "email_no_coincide" });
    }
    const yaReembolsado = p.status_detail === "refunded"
      || (typeof p.transaction_amount_refunded === "number"
          && p.transaction_amount_refunded >= p.transaction_amount);
    if (yaReembolsado) {
      return res.status(409).json({ error: "ya_reembolsado" });
    }
    const fechaAprobado = p.date_approved ? new Date(p.date_approved).getTime() : null;
    if (!fechaAprobado || Number.isNaN(fechaAprobado)) {
      return res.status(502).json({ error: "sin_fecha_aprobacion" });
    }
    const diasTranscurridos = (Date.now() - fechaAprobado) / 86400000;
    if (diasTranscurridos > VENTANA_DIAS) {
      return res.status(403).json({ error: "fuera_de_plazo", dias: Math.floor(diasTranscurridos) });
    }

    // 2) Las 3 condiciones se cumplen -> reembolso real (movimiento de plata).
    const rr = await fetch(
      `https://api.mercadopago.com/v1/payments/${encodeURIComponent(paymentId)}/refunds`,
      { method: "POST", headers: { authorization: `Bearer ${token}`, "content-type": "application/json" } },
    );
    if (!rr.ok) {
      const err = await rr.json().catch(() => ({}));
      return res.status(502).json({ error: "reembolso_fallo", detalle: err && err.message });
    }
    try { await revocarLicencia(email); } catch (e) { /* almacen no configurado: la plata igual se devolvio */ }
    return res.status(200).json({
      ok: true,
      mensaje: "Reembolso procesado. Puede tardar unos días en verse reflejado según tu medio de pago.",
    });
  } catch (e) {
    return res.status(502).json({ error: "fetch_fail" });
  }
}
