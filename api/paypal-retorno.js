// api/paypal-retorno.js — El comprador vuelve aca desde PayPal despues de
// aprobar (es el "return_url" de la orden creada en api/checkout.js).
//
// El pago NO se cobra hasta que se llama a /capture del lado del servidor:
// que el comprador haya vuelto a esta URL no significa que ya pago, asi que
// esto siempre captura server-side antes de dar nada por bueno (mismo
// principio que la verificacion server-side de MercadoPago en licencia.js).
// Idempotente: si el comprador recarga esta pagina, capturarOrden() detecta
// "ya capturada" en vez de fallar.
import { capturarOrden, obtenerOrden, leerOrden, paypalConfigurado } from "./_paypal.js";
import { otorgarBonoBienvenidaSiNuevo, acreditarRecargaSiNueva, esPackRecarga, PACKS_RECARGA } from "./_creditosia.js";
import { avisarCreditosPorEmail } from "./_email_creditos.js";
import { registrarVenta } from "./_atribucion.js";
import { limpiarRevocacion } from "./_revocacion.js";

export default async function handler(req, res) {
  if (!paypalConfigurado()) {
    res.setHeader("Location", "/#precios");
    return res.status(302).end();
  }
  const q = req.query || {};
  const ordenId = q.token;
  if (!ordenId) {
    res.setHeader("Location", "/#precios");
    return res.status(302).end();
  }

  try {
    const { yaCapturada, data } = await capturarOrden(ordenId);
    const orden = yaCapturada ? await obtenerOrden(ordenId) : data;
    const { plan, email, completado, cid, monto } = leerOrden(orden);
    if (!completado) {
      res.setHeader("Location", "/#precios");
      return res.status(302).end();
    }
    // Mismo criterio que en el flujo de MercadoPago (api/licencia.js): un
    // pago aprobado mintea/confirma la cuenta -> bono de bienvenida si es
    // nueva, y si el plan es un pack de creditos, se acredita. Idempotente
    // por ordenId (capturarOrden ya detecta "ya capturada", y esto ademas
    // evita acreditar dos veces si igual se llega aca).
    let bonoNuevo = null, recargaNueva = null;
    if (email) {
      try { bonoNuevo = await otorgarBonoBienvenidaSiNuevo(email); } catch (e) { /* almacen no configurado aun: no bloquea */ }
    }
    if (esPackRecarga(plan) && email) {
      try { recargaNueva = await acreditarRecargaSiNueva(email, ordenId, plan); } catch (e) { /* almacen no configurado aun: no bloquea */ }
    }
    // Email post-compra con el saldo, solo cuando el bono/la recarga fue
    // NUEVA (mismo criterio que api/licencia.js) -- recargar esta pagina de
    // retorno no manda el email de nuevo.
    if (bonoNuevo || recargaNueva) {
      try {
        await avisarCreditosPorEmail({
          email, bonoNuevo: Boolean(bonoNuevo),
          pack: recargaNueva ? PACKS_RECARGA[plan] : null,
          saldo: (recargaNueva || bonoNuevo).saldo,
        });
      } catch (e) { /* email caido/no configurado: no bloquea */ }
    }
    // Atribucion de venta (api/_atribucion.js): idempotente por ordenId, asi
    // que recargar esta pagina no la cuenta dos veces.
    try { await registrarVenta({ idPago: ordenId, plan, email, monto, proc: "paypal", cid }); }
    catch (e) { /* almacen no configurado: no bloquea el flujo de compra */ }
    // Un pago nuevo y aprobado es una compra legitima: levanta cualquier
    // revocacion previa de ese email (api/_revocacion.js).
    try { await limpiarRevocacion(email); } catch (e) { /* almacen no configurado: no bloquea */ }
    res.setHeader("Location", `/gracias.html?payment_id=${encodeURIComponent(ordenId)}&proc=paypal`);
    return res.status(302).end();
  } catch (e) {
    res.setHeader("Location", "/#precios");
    return res.status(302).end();
  }
}
