// api/reembolso.js — Reembolso AUTOMATICO de la garantia de 7 dias, via MercadoPago.
//
// Mueve plata real: todo se valida SERVER-SIDE contra MercadoPago, nunca contra
// lo que mande el cliente. Tres condiciones, las tres obligatorias:
//   1) El pago existe y esta "approved".
//   2) El email que manda el visitante coincide con el email real del pagador
//      (evita que alguien reembolse el pago de otra persona adivinando un
//      payment_id — el mismo riesgo de enumeracion que ya se mitigo en
//      api/licencia.js, pero aca con plata de por medio, asi que se re-valida).
//   3) Estan dentro de los 7 dias desde que el pago se aprobo (regla de negocio
//      real, no solo texto de marketing: se calcula con date_approved de MP).
//
// Recien si las tres se cumplen se llama al refund real de MercadoPago
// (POST /v1/payments/{id}/refunds, mismo patron de auth que ya usan
// checkout.js/licencia.js/descarga.js en este repo).
//
// LIMITE HONESTO (documentado, no escondido): esto devuelve la plata pero NO
// revoca la licencia emitida — no hay almacenamiento persistente en este
// proyecto (las claves son HMAC sin estado, sin una lista de "revocadas").
// Agregar revocacion real requeriria una base de datos (ej. Vercel KV/Upstash)
// que hoy no esta provisionada. Es un limite aceptado, no un bug escondido.
import { aplicarCors, clienteValido } from "./_seguridad.js";

const VENTANA_DIAS = 7;

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
  const paymentId = String(body.payment_id || "").trim();
  const email = String(body.email || "").trim().toLowerCase();
  if (!paymentId || !email) return res.status(400).json({ error: "faltan_datos" });

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
    return res.status(200).json({
      ok: true,
      mensaje: "Reembolso procesado. Puede tardar unos días en verse reflejado según tu medio de pago.",
    });
  } catch (e) {
    return res.status(502).json({ error: "fetch_fail" });
  }
}
