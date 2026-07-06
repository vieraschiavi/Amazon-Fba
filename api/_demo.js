// api/_demo.js — Registro server-side (solo de marketing, no de seguridad)
// de quien arranco la demo de 3 dias, para poder mandar un recordatorio
// antes de que venza si todavia no compro.
//
// IMPORTANTE -- esto NO cambia el modelo de seguridad de la demo: el reloj
// real de los 3 dias sigue viviendo en localStorage del cliente (ver
// mobile/js/licencia.js y core/licencia.py), y la licencia paga se sigue
// validando 100% server-side por HMAC (api/validar.js). Este registro es
// una copia lateral, best-effort, solo para poder mandar un email -- si
// falla o no esta configurado el almacen, la demo funciona exactamente igual
// que antes (el cliente nunca depende de esto).
//
// Requiere el mismo almacen (Vercel KV/Upstash) que ya usa la cuota de IA.
import { almacenConfigurado, kvGet, kvSet, kvPush, kvRango } from "./_almacen.js";
import { ultimasVentas } from "./_atribucion.js";

const MAX_INDICE = 2000;

function claveDemo(email) {
  return "demo:" + String(email || "").trim().toLowerCase();
}

export async function registrarDemo(nombre, email) {
  if (!almacenConfigurado() || !email) return null;
  const e = String(email).trim().toLowerCase();
  const ya = await kvGet(claveDemo(e));
  if (ya) return ya; // no pisar la fecha real de inicio si ya se habia registrado
  const registro = {
    nombre: String(nombre || "").slice(0, 100),
    email: e,
    fechaRegistro: new Date().toISOString(),
    recordatorioEnviado: false,
  };
  await kvSet(claveDemo(e), registro);
  await kvPush("demo:indice", e, MAX_INDICE);
  return registro;
}

export async function marcarRecordatorioEnviado(email) {
  const c = claveDemo(email);
  const reg = await kvGet(c);
  if (!reg) return null;
  reg.recordatorioEnviado = true;
  return kvSet(c, reg);
}

export async function listaDemos(cantidad) {
  if (!almacenConfigurado()) return [];
  const emails = await kvRango("demo:indice", 0, Math.max(0, cantidad - 1));
  const regs = await Promise.all(emails.map((e) => kvGet(claveDemo(e))));
  return regs.filter(Boolean);
}

// Best-effort: si no se puede determinar (almacen caido, etc.), asume que
// NO compro -- peor caso es un recordatorio de mas a alguien que ya pago,
// no perder el recordatorio a alguien que todavia no compro.
export async function yaComproPrevio(email) {
  try {
    const ventas = await ultimasVentas(1000);
    return ventas.some((v) => v.email && v.email.toLowerCase() === email.toLowerCase());
  } catch (e) {
    return false;
  }
}
