// api/ia.js — Proxy de IA para el DEMO web (asistente "IA incluida").
//
// La clave de Claude vive SOLO en la variable de entorno ANTHROPIC_API_KEY del
// proyecto de Vercel: nunca está en el repositorio ni se expone al visitante.
// Así el demo público de la web puede responder con IA real sin que nadie vea
// la clave. Topes puestos para proteger el presupuesto (modelo económico +
// max_tokens + largo de entrada acotado). Si la clave no está configurada, el
// endpoint responde 503 y la app cae sola al asistente local (sin romperse).
//
// En la versión DESCARGADA (APK/iOS/PC) este endpoint no existe: la app usa la
// clave propia del cliente (BYOK) o el asistente local. Por eso el fetch a
// /api/ia falla en file:// y cae al fallback — es el comportamiento buscado.

import { aplicarCors, clienteValido } from "./_seguridad.js";

const MODELO = "claude-haiku-4-5-20251001";   // económico, ideal para el demo
const MAX_TOKENS = 500;

export default async function handler(req, res) {
  aplicarCors(req, res, "POST, OPTIONS");
  if (req.method === "OPTIONS") return res.status(204).end();
  if (req.method !== "POST") return res.status(405).json({ error: "method" });
  if (!clienteValido(req)) return res.status(403).json({ error: "cliente_no_reconocido" });

  const key = process.env.ANTHROPIC_API_KEY;
  if (!key) return res.status(503).json({ error: "ia_no_configurada" });

  let body = req.body;
  if (typeof body === "string") { try { body = JSON.parse(body); } catch (e) { body = {}; } }
  body = body || {};
  const pregunta = String(body.pregunta || "").slice(0, 1500).trim();
  const contexto = String(body.contexto || "").slice(0, 4000);
  const idioma = String(body.idioma || "es").slice(0, 5);
  if (!pregunta) return res.status(400).json({ error: "sin_pregunta" });

  const system =
    "Sos el asistente de MV FBA IA, un cockpit para vender en Amazon FBA. " +
    "Respondés con un tono PROFESIONAL PERO AMABLE y cercano: claro, concreto y sin " +
    "relleno, pero cálido y respetuoso, como un asesor de confianza. En el idioma del " +
    "usuario (" + idioma + "). No prometés retornos garantizados: el resultado FBA es " +
    "variable. Nada reemplaza una orden de prueba antes de escalar. Es una versión DEMO: " +
    "respuestas breves y útiles.\n\nDATOS DEL NEGOCIO DEL USUARIO:\n" + contexto;

  try {
    const r = await fetch("https://api.anthropic.com/v1/messages", {
      method: "POST",
      headers: {
        "content-type": "application/json",
        "x-api-key": key,
        "anthropic-version": "2023-06-01",
      },
      body: JSON.stringify({
        model: MODELO,
        max_tokens: MAX_TOKENS,
        system,
        messages: [{ role: "user", content: pregunta }],
      }),
    });
    const data = await r.json();
    if (!r.ok) {
      return res.status(502).json({ error: "upstream", tipo: data && data.error && data.error.type });
    }
    const texto = (data.content || [])
      .filter((b) => b.type === "text").map((b) => b.text).join("").trim();
    return res.status(200).json({ texto: texto || "" });
  } catch (e) {
    return res.status(502).json({ error: "fetch_fail" });
  }
}
