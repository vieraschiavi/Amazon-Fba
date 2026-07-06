// api/_cuotaia.js — Cuota de IA del plan "Pro IA": renovacion (cada pago
// extiende 30 dias), verificacion antes de responder, y registro de consumo
// real (tokens de la respuesta de Claude, no una estimacion).
//
// Sin suscripcion automatica de MercadoPago (ver decision en el PR): cada
// pago de USD34 extiende la vigencia 30 dias. Si el cliente no vuelve a
// pagar, el acceso a IA incluida vence solo -- nunca hay un cobro
// automatico que "cancelar", asi que no hay forma de usarlo sin pagar.
//
// Si el almacen (Vercel KV/Upstash) no esta configurado, TODAS las
// funciones de aca devuelven "inactivo" de forma honesta -- no se inventa
// una cuota que no se puede contar de verdad (ver api/ia.js: sin esto,
// cae al comportamiento anterior con el tope generico anonimo).
import { kvGet, kvSet, almacenConfigurado } from "./_almacen.js";

const DIAS_VIGENCIA = 30;
// Punto de partida, no un numero definitivo: a precios tipicos de Claude
// Haiku, 500k tokens/mes cuestan unos pocos dolares -- deja margen sano
// sobre los USD34 del plan. Ajustable segun consumo real observado.
export const TOKENS_MES = 500000;
const TOPE_ACUMULADO_VECES = 2; // en modo "acumular", el saldo no pasa de 2x el cupo mensual

function clave(email) {
  return "cuota:" + String(email || "").trim().toLowerCase();
}
function claveIdPago(idPago) {
  return "pago_procesado:" + String(idPago || "").trim();
}

// Version idempotente de renovarPlanIA: si gracias.html se recarga (o el
// comprador vuelve atras y adelante), NO hay que regalar otros 30 dias por
// el MISMO pago. Se marca el id de pago/orden como procesado antes de
// renovar, y si ya estaba marcado, no hace nada.
export async function renovarPlanIASiNuevo(email, idPago) {
  if (!almacenConfigurado() || !idPago) return null;
  const marcador = claveIdPago(idPago);
  const yaProcesado = await kvGet(marcador);
  if (yaProcesado) return null;
  await kvSet(marcador, true);
  return renovarPlanIA(email);
}

export async function renovarPlanIA(email) {
  if (!almacenConfigurado()) return null;
  const k = clave(email);
  const actual = (await kvGet(k)) || {};
  const ahora = new Date();
  const vigenteHastaActual = actual.vigente_hasta ? new Date(actual.vigente_hasta) : null;
  // Si ya estaba vigente, extiende desde el vencimiento (no desde hoy) para
  // no "perder" dias por pagar unos dias antes de que venza.
  const base = (vigenteHastaActual && vigenteHastaActual > ahora) ? vigenteHastaActual : ahora;
  const vigenteHasta = new Date(base.getTime() + DIAS_VIGENCIA * 86400000);
  const modo = actual.cuota_modo === "acumular" ? "acumular" : "topear";
  const sobrante = Math.max(0, TOKENS_MES - (actual.tokens_usados_periodo || 0));
  const registro = {
    vigente_hasta: vigenteHasta.toISOString(),
    cuota_modo: modo,
    periodo_inicio: ahora.toISOString(),
    tokens_usados_periodo: 0,
    tokens_acumulados: modo === "acumular"
      ? Math.min((actual.tokens_acumulados || 0) + sobrante, TOKENS_MES * TOPE_ACUMULADO_VECES)
      : 0,
  };
  await kvSet(k, registro);
  return registro;
}

export async function fijarModoCuota(email, modo) {
  if (!almacenConfigurado()) return null;
  if (modo !== "topear" && modo !== "acumular") throw new Error("modo_invalido");
  const k = clave(email);
  const actual = (await kvGet(k)) || {};
  const registro = { ...actual, cuota_modo: modo };
  await kvSet(k, registro);
  return registro;
}

export async function revisarCuota(email) {
  if (!almacenConfigurado()) return { activo: false, motivo: "almacen_no_configurado" };
  const registro = await kvGet(clave(email));
  if (!registro) return { activo: false, motivo: "sin_plan_ia" };
  const vigente = registro.vigente_hasta && new Date(registro.vigente_hasta) > new Date();
  if (!vigente) return { activo: false, motivo: "plan_vencido", registro };
  const disponible = TOKENS_MES + (registro.tokens_acumulados || 0) - (registro.tokens_usados_periodo || 0);
  if (disponible <= 0) return { activo: false, motivo: "cuota_agotada", registro };
  return { activo: true, disponible, registro };
}

export async function registrarConsumo(email, tokens) {
  if (!almacenConfigurado() || !(tokens > 0)) return;
  const k = clave(email);
  const actual = await kvGet(k);
  if (!actual) return;
  actual.tokens_usados_periodo = (actual.tokens_usados_periodo || 0) + tokens;
  await kvSet(k, actual);
}
