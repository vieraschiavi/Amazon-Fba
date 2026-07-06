// api/_atribucion.js — De donde vino cada venta (que red social/campana),
// para poder comparar contra el esfuerzo de marketing que se invierte en cada
// uno de los 4 proyectos. Sin esto no habia forma de saber si una venta vino
// de una red o de otro lado.
//
// Flujo: landing/index.html genera un "cid" (correlation id) al hacer click
// en Comprar y guarda los UTM de la URL contra ese cid ANTES de ir a
// MercadoPago/PayPal (guardarUtm). El cid viaja dentro del pago (metadata de
// MercadoPago, custom_id de PayPal). Cuando el pago se confirma en
// api/licencia.js, se relee el cid, se busca el UTM guardado, y se deja un
// registro final de venta (registrarVenta) que api/ventas.js puede agregar
// por canal/plan.
//
// Requiere el mismo almacen (Vercel KV/Upstash) que ya usa la cuota de IA: si
// no esta configurado, todo esto es un no-op (no bloquea checkout ni
// licencia, simplemente no queda atribucion).
import { almacenConfigurado, kvGet, kvSet, kvPush, kvRango } from "./_almacen.js";

const TTL_UTM_SEGUNDOS = 60 * 60 * 24 * 30; // 30 dias: un checkout abandonado mas viejo que esto ya no importa
const MAX_VENTAS_INDICE = 1000;

function claveUtm(cid) {
  return "utm:" + String(cid || "").trim();
}
function claveVenta(idPago) {
  return "venta:" + String(idPago || "").trim();
}

export async function guardarUtm(cid, utm) {
  if (!almacenConfigurado() || !cid) return null;
  return kvSet(claveUtm(cid), utm || {}, TTL_UTM_SEGUNDOS);
}

async function leerUtm(cid) {
  if (!almacenConfigurado() || !cid) return null;
  try { return await kvGet(claveUtm(cid)); } catch (e) { return null; }
}

// Idempotente por idPago: gracias.html puede recargar y volver a llamar a
// api/licencia.js para el MISMO pago -- no hay que duplicar el registro ni
// re-contarlo en las estadisticas cada vez que se recarga la pagina.
export async function registrarVenta({ idPago, plan, email, monto, proc, cid }) {
  if (!almacenConfigurado() || !idPago) return null;
  const ya = await kvGet(claveVenta(idPago));
  if (ya) return null;
  const utm = await leerUtm(cid);
  const registro = {
    idPago, plan: plan || "", email: email || "", monto: monto || null,
    proc: proc || "mercadopago", utm: utm || null, fecha: new Date().toISOString(),
  };
  await kvSet(claveVenta(idPago), registro);
  await kvPush("ventas:indice", idPago, MAX_VENTAS_INDICE);
  return registro;
}

// Usado por api/ventas.js (reporte de administracion) para traer las ultimas
// N ventas ya resueltas (no solo el indice de ids).
export async function ultimasVentas(cantidad) {
  if (!almacenConfigurado()) return [];
  const ids = await kvRango("ventas:indice", 0, Math.max(0, cantidad - 1));
  const ventas = await Promise.all(ids.map((id) => kvGet(claveVenta(id))));
  return ventas.filter(Boolean);
}
