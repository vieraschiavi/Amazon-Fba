// api/_almacen.js — Cliente minimo (fetch puro, sin SDK) para Vercel KV /
// Upstash Redis via su API REST. El prefijo "_" hace que Vercel NO trate
// este archivo como una ruta.
//
// Se usa SOLO para lo que de verdad necesita persistir entre llamadas: la
// cuota de IA del plan "Pro IA" (cuanto goasto cada licencia este periodo,
// y hasta cuando esta pago). Todo lo demas del sistema (licencias, CORS)
// sigue siendo sin estado a proposito.
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

export async function kvSet(clave, valor) {
  return comando(["set", clave, JSON.stringify(valor)]);
}
