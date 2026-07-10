// api/_revocacion.js — Revocacion real de licencia al reembolsar (limitacion
// que habia quedado documentada como pendiente en api/reembolso.js).
//
// Sin esto, alguien podia pedir el reembolso de 7 dias y seguir usando la
// licencia para siempre -- el HMAC de generarClave() no tiene forma de saber
// que ese pago ya se devolvio. Esto agrega un flag en el almacen (Vercel
// KV/Upstash) que api/validar.js chequea ADEMAS del HMAC.
//
// Requiere el mismo almacen que ya usa el saldo de creditos de IA (ver
// api/_creditosia.js): si no esta configurado, no rompe nada -- simplemente
// no hay revocacion (mismo comportamiento honesto de "sin almacen, sin esta
// funcion" del resto del sistema).
import { almacenConfigurado, kvGet, kvSet } from "./_almacen.js";

function clave(email) {
  return "licencia_revocada:" + String(email || "").trim().toLowerCase();
}

export async function revocarLicencia(email) {
  if (!almacenConfigurado() || !email) return null;
  return kvSet(clave(email), true);
}

// Se llama cuando un pago NUEVO y aprobado emite licencia: si ese email tenia
// una revocacion de una compra anterior, un pago legitimo nuevo la levanta --
// no tiene sentido seguir bloqueando a alguien que volvio a pagar de verdad.
export async function limpiarRevocacion(email) {
  if (!almacenConfigurado() || !email) return null;
  return kvSet(clave(email), false);
}

export async function licenciaRevocada(email) {
  if (!almacenConfigurado() || !email) return false;
  return Boolean(await kvGet(clave(email)));
}
