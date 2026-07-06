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
import { renovarPlanIASiNuevo } from "./_cuotaia.js";
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
    // Plan "Pro IA": el mismo pago aprobado extiende 30 dias de cuota,
    // igual que en el flujo de MercadoPago (api/licencia.js). Idempotente
    // por ordenId: si el comprador recarga esta pagina de retorno, no
    // regala dias de mas (capturarOrden ya detecta "ya capturada", y esto
    // ademas evita renovar dos veces la cuota si igual se llega aca).
    if (plan === "ia" && email) {
      try { await renovarPlanIASiNuevo(email, ordenId); } catch (e) { /* almacen no configurado aun: no bloquea */ }
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
