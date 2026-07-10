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
import { otorgarBonoBienvenidaSiNuevo, acreditarRecargaSiNueva, esPackRecarga } from "./_creditosia.js";
import { obtenerOrden, leerOrden, paypalConfigurado } from "./_paypal.js";
import { limpiarRevocacion } from "./_revocacion.js";
import { registrarVenta } from "./_atribucion.js";

export default async function handler(req, res) {
  aplicarCors(req, res, "GET, OPTIONS");
  if (req.method === "OPTIONS") return res.status(204).end();
  // Defensa en profundidad: sin esto, un bot podria enumerar payment_id al
  // azar buscando pagos aprobados de OTRAS personas para pescar su email +
  // licencia. El header no detiene a un atacante dirigido, pero saca del
  // medio el escaneo automatico generico.
  if (!clienteValido(req)) return res.status(403).json({ error: "cliente_no_reconocido" });

  const q = req.query || {};
  const paymentId = q.payment_id || q.collection_id || q.paymentId;
  if (!paymentId) return res.status(400).json({ error: "sin_pago" });

  // PayPal: la orden ya se capturo en api/paypal-retorno.js (y esa vez ya se
  // otorgo el bono/acredito la recarga). Aca solo se relee el estado para
  // mostrar la licencia -- NO se vuelve a acreditar, para no duplicar
  // creditos si el comprador recarga gracias.html.
  if (String(q.proc || "") === "paypal") {
    if (!paypalConfigurado()) return res.status(503).json({ error: "pago_no_configurado" });
    try {
      const orden = await obtenerOrden(paymentId);
      const { plan, email, completado, estado } = leerOrden(orden);
      if (!completado) return res.status(200).json({ aprobado: false, estado });
      return res.status(200).json({ aprobado: true, plan, email, licencia: generarClave(email) });
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
    if (p.status !== "approved") {
      return res.status(200).json({ aprobado: false, estado: p.status });
    }
    const email = (p.payer && p.payer.email) || "";
    const plan = p.external_reference || (p.metadata && p.metadata.plan) || "";
    const cid = (p.metadata && p.metadata.cid) || "";
    // Cualquier pago aprobado mintea/confirma una cuenta con licencia: si es
    // la primera vez que este email compra algo, se le otorga el bono de
    // bienvenida en creditos de IA (ver api/_creditosia.js). Es idempotente
    // por email, asi que no importa si esto corre de nuevo en un pago futuro.
    if (email) {
      try { await otorgarBonoBienvenidaSiNuevo(email); } catch (e) { /* almacen no configurado aun: no bloquea la licencia */ }
    }
    // Si el plan es un pack de recarga de creditos, se acredita ademas del
    // bono (idempotente por paymentId: recargar gracias.html no acredita el
    // mismo pack dos veces).
    if (esPackRecarga(plan) && email) {
      try { await acreditarRecargaSiNueva(email, paymentId, plan); } catch (e) { /* almacen no configurado aun: no bloquea la licencia */ }
    }
    // Un pago nuevo y aprobado es una compra legitima: si ese email tenia una
    // licencia revocada por un reembolso anterior, la levanta (api/_revocacion.js).
    try { await limpiarRevocacion(email); } catch (e) { /* almacen no configurado: no bloquea */ }
    // Atribucion de venta (api/_atribucion.js): idempotente por paymentId.
    try { await registrarVenta({ idPago: paymentId, plan, email, monto: p.transaction_amount, proc: "mercadopago", cid }); }
    catch (e) { /* almacen no configurado: no bloquea la licencia */ }
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
