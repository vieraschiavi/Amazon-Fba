// api/_creditosia.js — Saldo de creditos de IA compartida (el asistente usa
// la clave de Claude del negocio, no la del cliente). Reemplaza el modelo
// anterior de cuota mensual fija (api/_cuotaia.js, plan "Pro IA" $34/mes que
// se reseteaba cada renovacion) por un SALDO que:
//
//   - arranca con un bono de bienvenida gratis apenas la cuenta existe (se
//     otorga al mintear la licencia por CUALQUIER pago aprobado — starter,
//     pro, o un pack de creditos — ver api/licencia.js);
//   - se recarga comprando un pack de creditos por MercadoPago/PayPal
//     (api/checkout.js + api/licencia.js), y NO vence con el tiempo;
//   - se descuenta segun el consumo REAL de tokens de cada respuesta de
//     Claude (data.usage, no una estimacion — ver api/ia.js), convertido a
//     creditos con margen sobre el costo real de la nube.
//
// Por que no aplica durante la demo de 3 dias (antes de comprar algo): esta
// libreria identifica cuentas por email+clave de licencia VALIDADA (HMAC,
// api/_licencia.js). Durante la demo no existe ese par todavia (ver
// core/licencia.py: clave_licencia es None hasta activar_licencia) — aceptar
// creditos solo por email de texto plano (sin prueba de dueño) se podria
// abusar creando emails al voleo para juntar bonos gratis infinitos, o para
// vaciarle el saldo a otra persona adivinando su email. La demo se sigue
// sirviendo con el tope generico anonimo por dispositivo (ver api/ia.js).
//
// Sin almacen (Vercel KV/Upstash) configurado, todo esto devuelve "sin saldo"
// de forma honesta — no se inventa un saldo que no se puede contar de verdad
// (mismo criterio que _cuotaia.js).
import { kvGet, kvSet, almacenConfigurado } from "./_almacen.js";

// Bono de bienvenida: alcanza para probar el asistente unas 40-60 preguntas
// segun el largo de la respuesta. Punto de partida, no un numero definitivo
// — ajustable segun consumo real observado (mismo criterio que TOKENS_MES en
// _cuotaia.js).
export const BONO_BIENVENIDA = 200;

// Conversion tokens -> creditos. A precios tipicos de Claude Haiku, 1000
// tokens (entrada+salida) cuestan una fraccion de centavo de USD real: el
// pack mas chico (US$9 -> 6000 creditos = 6.000.000 tokens) rinde muy por
// encima del costo real en la nube, dejando margen sano. Ajustable.
const TOKENS_POR_CREDITO = 1000;

// Packs de recarga (reemplazan el viejo plan "ia" fijo de checkout.js). Las
// claves ("creditos_9" etc.) son el "plan" que viaja en la preferencia de
// pago (external_reference / metadata.plan) y que api/licencia.js usa para
// saber cuanto acreditar.
export const PACKS_RECARGA = {
  creditos_9:  { titulo: "MV FBA IA — Recarga de créditos (chica)",  precio: 9,  creditos: 6000 },
  creditos_19: { titulo: "MV FBA IA — Recarga de créditos (media)",  precio: 19, creditos: 14000 },
  creditos_34: { titulo: "MV FBA IA — Recarga de créditos (grande)", precio: 34, creditos: 28000 },
};

export function esPackRecarga(plan) {
  return Object.prototype.hasOwnProperty.call(PACKS_RECARGA, String(plan || ""));
}

function clave(email) {
  return "creditos:" + String(email || "").trim().toLowerCase();
}
function claveIdPago(idPago) {
  return "credito_pago_procesado:" + String(idPago || "").trim();
}

// Idempotente por email: si la cuenta ya tiene un registro de creditos (ya
// se le otorgo el bono antes, o ya recargo), no lo pisa ni le regala otro
// bono. Se llama tanto al mintear una licencia nueva como, por las dudas,
// antes de acreditar una recarga (para cubrir a alguien que compra directo
// sin haber tenido licencia previa).
//
// Devuelve el registro SOLO cuando el bono se otorgo AHORA; null si la
// cuenta ya existia (misma semantica "SiNuevo/SiNueva" que
// acreditarRecargaSiNueva). Eso es lo que deja a api/licencia.js decidir si
// corresponde el email de bienvenida sin mandarlo de nuevo en cada pago.
export async function otorgarBonoBienvenidaSiNuevo(email) {
  if (!almacenConfigurado() || !email) return null;
  const k = clave(email);
  const actual = await kvGet(k);
  if (actual) return null;
  const registro = {
    saldo: BONO_BIENVENIDA,
    otorgado: new Date().toISOString(),
    historico_recargado: 0,
    historico_consumido: 0,
  };
  await kvSet(k, registro);
  return registro;
}

// conLicenciaValidada: el llamador YA verifico email+clave por HMAC
// (claveValida). En ese caso, una cuenta sin registro de creditos recibe el
// bono de bienvenida al vuelo: cubre a los clientes que compraron ANTES de
// que existiera este sistema (su pago nunca paso por el otorgamiento de
// api/licencia.js) sin regalarle nada a nadie sin licencia real.
export async function revisarSaldo(email, conLicenciaValidada = false) {
  if (!almacenConfigurado()) return { activo: false, motivo: "almacen_no_configurado" };
  let registro = await kvGet(clave(email));
  if (!registro && conLicenciaValidada) {
    registro = await otorgarBonoBienvenidaSiNuevo(email);
  }
  if (!registro) return { activo: false, motivo: "sin_cuenta" };
  if (!(registro.saldo > 0)) return { activo: false, motivo: "saldo_agotado", registro };
  return { activo: true, saldo: registro.saldo, registro };
}

// Clave de semana ISO-ish (lunes como inicio) para el resumen "esta semana
// usaste X creditos en Y preguntas" -- no hace falta el numero de semana ISO
// exacto, solo que la clave cambie una vez por semana de forma estable.
function semanaActual() {
  const d = new Date();
  const lunes = new Date(d);
  lunes.setUTCDate(d.getUTCDate() - ((d.getUTCDay() + 6) % 7));
  return lunes.toISOString().slice(0, 10); // fecha del lunes de esta semana
}

// Devuelve el registro actualizado (con el saldo ya descontado) para que el
// llamador pueda informar "te quedan N creditos" sin otra lectura. Ademas
// acumula el resumen semanal (creditos + preguntas) que muestran las UIs.
export async function descontarCreditos(email, tokens) {
  if (!almacenConfigurado() || !(tokens > 0)) return null;
  const k = clave(email);
  const actual = await kvGet(k);
  if (!actual) return null; // sin registro de creditos: nada que descontar
  const creditos = tokens / TOKENS_POR_CREDITO;
  actual.saldo = Math.max(0, (actual.saldo || 0) - creditos);
  actual.historico_consumido = (actual.historico_consumido || 0) + creditos;
  actual.n_preguntas = (actual.n_preguntas || 0) + 1;
  const semana = semanaActual();
  if (actual.semana !== semana) {
    actual.semana = semana;
    actual.semana_consumido = 0;
    actual.semana_preguntas = 0;
  }
  actual.semana_consumido = (actual.semana_consumido || 0) + creditos;
  actual.semana_preguntas = (actual.semana_preguntas || 0) + 1;
  await kvSet(k, actual);
  return actual;
}

// Version idempotente por paymentId: si gracias.html se recarga (o el
// comprador vuelve atras y adelante), NO hay que acreditar el mismo pack dos
// veces por el MISMO pago.
export async function acreditarRecargaSiNueva(email, idPago, plan) {
  if (!almacenConfigurado() || !idPago) return null;
  const pack = PACKS_RECARGA[plan];
  if (!pack) return null;
  const marcador = claveIdPago(idPago);
  const yaProcesado = await kvGet(marcador);
  if (yaProcesado) return null;
  await kvSet(marcador, true);
  await otorgarBonoBienvenidaSiNuevo(email);
  const k = clave(email);
  const actual = (await kvGet(k)) || { saldo: 0, historico_recargado: 0, historico_consumido: 0 };
  actual.saldo = (actual.saldo || 0) + pack.creditos;
  actual.historico_recargado = (actual.historico_recargado || 0) + pack.creditos;
  await kvSet(k, actual);
  return actual;
}
