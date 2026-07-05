// api/validar.js — Valida una licencia DEL LADO DEL SERVIDOR.
//
// El secreto de firma vive SOLO en la variable de entorno LICENCIA_SECRETO de
// Vercel — nunca en el cliente. Así nadie puede auto-generarse una licencia
// leyendo el código: la app manda {email, clave} aquí y el servidor responde
// si es válida. La misma fórmula HMAC la usa api/licencia.js para emitirla tras
// el pago. La activación pide internet una vez; luego la app funciona offline.
import crypto from "crypto";

const SECRETO = process.env.LICENCIA_SECRETO || "mv-amazon-fba-2026-clave-de-firma";
const DOMINIO = "MV-Amazon-Fba";

function generarClave(email) {
  const base = String(email || "").trim().toLowerCase() + DOMINIO;
  const hex = crypto.createHmac("sha256", SECRETO).update(base).digest("hex").toUpperCase().slice(0, 16);
  return "MVFBA-" + [hex.slice(0, 4), hex.slice(4, 8), hex.slice(8, 12), hex.slice(12, 16)].join("-");
}

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

  const valido = clave === generarClave(email);
  return res.status(200).json({ valido });
}
