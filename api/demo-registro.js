// api/demo-registro.js — Copia lateral, best-effort, de "alguien arranco la
// demo de 3 dias" (ver api/_demo.js). Lo llama mobile/js/licencia.js al
// registrarse, en paralelo al localStorage local -- si esto falla o el
// visitante no tiene internet en ese instante, la demo sigue funcionando
// igual (el reloj real vive en el cliente).
//
// Sin CORS restringido ni header de app a proposito: lo llaman la PWA/app
// desde file:// o dominios de instalacion variados, mismo criterio que
// api/validar.js. No mueve plata ni expone nada sensible -- en el peor caso,
// alguien manda nombre/email de mentira, que como mucho ensucia un
// recordatorio de marketing, no un riesgo de seguridad.
import { registrarDemo } from "./_demo.js";

export default async function handler(req, res) {
  res.setHeader("Access-Control-Allow-Origin", "*");
  res.setHeader("Access-Control-Allow-Headers", "Content-Type");
  res.setHeader("Access-Control-Allow-Methods", "POST, OPTIONS");
  if (req.method === "OPTIONS") return res.status(204).end();
  if (req.method !== "POST") return res.status(405).json({ error: "method" });

  let body = req.body;
  if (typeof body === "string") { try { body = JSON.parse(body); } catch (e) { body = {}; } }
  body = body || {};
  const email = String(body.email || "").trim().toLowerCase();
  const nombre = String(body.nombre || "").trim();
  if (!email || !email.includes("@")) return res.status(200).json({ ok: false });

  try {
    await registrarDemo(nombre, email);
  } catch (e) { /* almacen no configurado: no bloquea, no rompe la demo */ }
  return res.status(200).json({ ok: true });
}
