// api/validar.js — Valida una licencia DEL LADO DEL SERVIDOR.
//
// El secreto de firma vive SOLO en la variable de entorno LICENCIA_SECRETO de
// Vercel — nunca en el cliente. Así nadie puede auto-generarse una licencia
// leyendo el código: la app manda {email, clave} aquí y el servidor responde
// si es válida. La misma fórmula HMAC la usa api/licencia.js para emitirla tras
// el pago. La activación pide internet una vez; luego la app funciona offline.
//
// A DIFERENCIA de los endpoints web (checkout/ia/mercado/licencia), este NO
// restringe CORS ni pide el header de aplicación: lo llaman el programa de PC,
// la app Android y iOS (WebView / file://), donde el navegador no manda el
// mismo Origin que un sitio web — restringirlo rompería la activación de
// clientes que ya pagaron. Su protección real es otra: el HMAC es imposible
// de adivinar por fuerza bruta y no hay ningún costo (Claude/Keepa/pago) detrás
// de cada intento, así que no es un objetivo valioso para un bot.
import { claveValida } from "./_licencia.js";
import { licenciaRevocada } from "./_revocacion.js";

export default async function handler(req, res) {
  res.setHeader("Access-Control-Allow-Origin", "*");
  res.setHeader("Access-Control-Allow-Headers", "Content-Type");
  res.setHeader("Access-Control-Allow-Methods", "POST, OPTIONS");
  if (req.method === "OPTIONS") return res.status(204).end();
  if (req.method !== "POST") return res.status(405).json({ error: "method" });

  let body = req.body;
  if (typeof body === "string") { try { body = JSON.parse(body); } catch (e) { body = {}; } }
  body = body || {};
  const email = String(body.email || "").slice(0, 160);
  const clave = String(body.clave || "").slice(0, 40).trim().toUpperCase();
  if (!email || !clave) return res.status(400).json({ valido: false, error: "faltan_datos" });

  if (!claveValida(email, clave)) return res.status(200).json({ valido: false });

  // El HMAC por si solo no sabe si ese pago ya se reembolso -- se chequea
  // aparte contra el flag que pone api/reembolso.js (best-effort: si el
  // almacen no esta configurado, licenciaRevocada() devuelve false y el
  // comportamiento queda igual que antes de esta funcion).
  let revocada = false;
  try { revocada = await licenciaRevocada(email); } catch (e) { revocada = false; }
  return res.status(200).json({ valido: !revocada });
}
