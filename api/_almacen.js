// api/_almacen.js — Cliente minimo (fetch puro, sin SDK) para Vercel KV /
// Upstash Redis via su API REST. El prefijo "_" hace que Vercel NO trate
// este archivo como una ruta.
//
// Se usa para lo que de verdad necesita persistir entre llamadas: la cuota de
// IA del plan "Pro IA", licencias revocadas por reembolso, atribucion de
// ventas (que campana/red social trajo cada compra) y registros de demo para
// el recordatorio por email. La validacion de licencia en si (HMAC) sigue
// siendo sin estado a proposito -- esto es historial/analitica, no seguridad.
//
// Variables de entorno esperadas (las inyecta Vercel solo al conectar el
// storage "KV" o "Upstash for Redis" desde el dashboard del proyecto):
//   KV_REST_API_URL, KV_REST_API_TOKEN

const BASE = process.env.KV_REST_API_URL;
const TOKEN = process.env.KV_REST_API_TOKEN;

export function almacenConfigurado() {
  return Boolean(BASE && TOKEN);
}

async function comando(partes) {
  if (!almacenConfigurado()) throw new Error("almacen_no_configurado");
  const url = BASE + "/" + partes.map((p) => encodeURIComponent(String(p))).join("/");
  const r = await fetch(url, { headers: { Authorization: `Bearer ${TOKEN}` } });
  const d = await r.json();
  if (d && d.error) throw new Error("kv_error: " + d.error);
  return d ? d.result : null;
}

export async function kvGet(clave) {
  const v = await comando(["get", clave]);
  if (v == null) return null;
  try { return JSON.parse(v); } catch (e) { return v; }
}

// ttlSegundos opcional: para datos de vida corta (ej. atribucion de UTM de un
// checkout que puede no completarse nunca) asi no se acumulan para siempre.
export async function kvSet(clave, valor, ttlSegundos) {
  const partes = ["set", clave, JSON.stringify(valor)];
  if (ttlSegundos) partes.push("EX", ttlSegundos);
  return comando(partes);
}

// Lista acotada (LPUSH + LTRIM): un indice barato de los ultimos N registros
// (ventas, demos) sin tener que escanear todo el keyspace de Redis -- la API
// REST de Upstash no ofrece SCAN economico a este volumen/plan.
export async function kvPush(lista, valor, maxItems) {
  await comando(["lpush", lista, JSON.stringify(valor)]);
  if (maxItems) await comando(["ltrim", lista, "0", String(maxItems - 1)]);
}

export async function kvRango(lista, desde, hasta) {
  const items = await comando(["lrange", lista, String(desde), String(hasta)]);
  if (!Array.isArray(items)) return [];
  return items.map((v) => { try { return JSON.parse(v); } catch (e) { return v; } });
}
