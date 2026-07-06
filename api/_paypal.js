// api/_paypal.js — Cliente minimo (fetch puro, sin SDK) para la API REST de
// PayPal Orders v2. El prefijo "_" hace que Vercel NO trate este archivo
// como una ruta.
//
// PAYPAL_SANDBOX=true usa el entorno de pruebas (api-m.sandbox.paypal.com);
// sin esa variable (o en cualquier otro valor) usa el entorno real
// (api-m.paypal.com). Las credenciales viven SOLO en variables de entorno
// de Vercel, nunca en el repo ni en el cliente.
const SANDBOX = String(process.env.PAYPAL_SANDBOX || "").toLowerCase() === "true";
const BASE = SANDBOX ? "https://api-m.sandbox.paypal.com" : "https://api-m.paypal.com";

export function paypalConfigurado() {
  return Boolean(process.env.PAYPAL_CLIENT_ID && process.env.PAYPAL_CLIENT_SECRET);
}

async function obtenerToken() {
  const id = process.env.PAYPAL_CLIENT_ID;
  const secreto = process.env.PAYPAL_CLIENT_SECRET;
  if (!id || !secreto) throw new Error("paypal_no_configurado");
  const auth = Buffer.from(`${id}:${secreto}`).toString("base64");
  const r = await fetch(`${BASE}/v1/oauth2/token`, {
    method: "POST",
    headers: { Authorization: `Basic ${auth}`, "Content-Type": "application/x-www-form-urlencoded" },
    body: "grant_type=client_credentials",
  });
  const d = await r.json();
  if (!r.ok) throw new Error("paypal_oauth_fallo: " + (d && (d.error_description || d.error)));
  return d.access_token;
}

// Crea una orden (intent CAPTURE) y devuelve el link de aprobacion al que
// hay que redirigir al comprador — mismo rol que "init_point" de MercadoPago.
export async function crearOrden({ monto, moneda, referencia, returnUrl, cancelUrl, descripcion }) {
  const token = await obtenerToken();
  const r = await fetch(`${BASE}/v2/checkout/orders`, {
    method: "POST",
    headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json" },
    body: JSON.stringify({
      intent: "CAPTURE",
      purchase_units: [{
        reference_id: referencia,
        custom_id: referencia,
        description: descripcion,
        amount: { currency_code: moneda, value: monto },
      }],
      application_context: {
        return_url: returnUrl,
        cancel_url: cancelUrl,
        brand_name: "MV FBA IA",
        user_action: "PAY_NOW",
        shipping_preference: "NO_SHIPPING",
      },
    }),
  });
  const d = await r.json();
  if (!r.ok) throw new Error("paypal_orden_fallo: " + JSON.stringify(d));
  const aprobar = (d.links || []).find((l) => l.rel === "approve" || l.rel === "payer-action");
  return { id: d.id, aprobarUrl: aprobar && aprobar.href };
}

// Cobra de verdad la orden aprobada. Idempotente: si ya estaba capturada
// (el comprador recargo la pagina de vuelta, por ejemplo), lo informa en
// vez de tratarlo como error.
export async function capturarOrden(ordenId) {
  const token = await obtenerToken();
  const r = await fetch(`${BASE}/v2/checkout/orders/${encodeURIComponent(ordenId)}/capture`, {
    method: "POST",
    headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json" },
  });
  const d = await r.json();
  const yaCapturada = !r.ok && d && Array.isArray(d.details)
    && d.details.some((x) => x.issue === "ORDER_ALREADY_CAPTURED");
  if (!r.ok && !yaCapturada) throw new Error("paypal_captura_fallo: " + JSON.stringify(d));
  return { yaCapturada, data: d };
}

export async function obtenerOrden(ordenId) {
  const token = await obtenerToken();
  const r = await fetch(`${BASE}/v2/checkout/orders/${encodeURIComponent(ordenId)}`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  const d = await r.json();
  if (!r.ok) throw new Error("paypal_get_orden_fallo: " + JSON.stringify(d));
  return d;
}

// Extrae {plan, email, completado, captura} de una orden (recien creada,
// capturada, o consultada) de forma uniforme, sin repetir esta logica en
// cada endpoint. "captura" trae el id + fecha + si ya fue reembolsada, que
// necesita api/reembolso.js.
export function leerOrden(orden) {
  const pu = (orden.purchase_units || [])[0] || {};
  const capturas = (pu.payments && pu.payments.captures) || [];
  const capturaOk = capturas.find((c) => c.status === "COMPLETED");
  const completado = orden.status === "COMPLETED" || Boolean(capturaOk);
  return {
    plan: pu.reference_id || pu.custom_id || "",
    email: (orden.payer && orden.payer.email_address) || "",
    completado,
    estado: orden.status,
    captura: capturaOk ? {
      id: capturaOk.id,
      creada: capturaOk.create_time,
      reembolsada: (capturas.find((c) => c.status === "REFUNDED")) ? true : false,
    } : null,
  };
}

// Reembolso total de una captura ya cobrada (garantia de 7 dias). Idempotente
// del lado de PayPal: si ya estaba reembolsada, la API devuelve un error que
// se distingue por el "issue" CAPTURE_FULLY_REFUNDED.
export async function reembolsarCaptura(captureId) {
  const token = await obtenerToken();
  const r = await fetch(`${BASE}/v2/payments/captures/${encodeURIComponent(captureId)}/refund`, {
    method: "POST",
    headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json" },
  });
  const d = await r.json();
  const yaReembolsada = !r.ok && d && Array.isArray(d.details)
    && d.details.some((x) => x.issue === "CAPTURE_FULLY_REFUNDED");
  if (!r.ok && !yaReembolsada) throw new Error("paypal_reembolso_fallo: " + JSON.stringify(d));
  return { yaReembolsada, data: d };
}
