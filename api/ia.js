// api/ia.js — Proxy de IA para el DEMO web y para cuentas con licencia y
// saldo de creditos (ver api/_creditosia.js).
//
// La clave de Claude vive SOLO en la variable de entorno ANTHROPIC_API_KEY del
// proyecto de Vercel: nunca está en el repositorio ni se expone al visitante.
// Dos niveles de acceso, cada uno con su tope real (nunca ilimitado):
//
//   1) Con {email, clave} de una licencia real y saldo de creditos > 0 (bono
//      de bienvenida y/o recargas — ver api/_creditosia.js): se descuenta el
//      consumo REAL de la respuesta de Claude (data.usage), no una estimacion.
//      Sin base de datos (Vercel KV/Upstash) configurada, esto no se puede
//      contar de verdad -> cae al nivel 2 en vez de fingir un saldo.
//   2) Sin licencia o sin saldo de creditos (demo de 3 dias, o cuenta que ya
//      gasto todo su saldo): tope generico por dispositivo, bajo, para que
//      nadie use esto gratis sin limite. Es un tope "blando" (localStorage
//      puede reinstalarse) -- frena el abuso casual, no a un atacante
//      dedicado; para eso corresponde el Firewall de Vercel (ver
//      api/_seguridad.js).
//
// En la versión DESCARGADA (APK/iOS/PC) sin clave propia (BYOK), la app llama
// a este mismo endpoint como fallback -- por eso valida licencia acá y no
// confía en lo que diga el cliente.
import { aplicarCors, clienteValido } from "./_seguridad.js";
import { claveValida } from "./_licencia.js";
import { revisarSaldo, descontarCreditos } from "./_creditosia.js";
import { kvGet, kvSet, almacenConfigurado } from "./_almacen.js";

const MODELO = "claude-haiku-4-5-20251001";   // económico
const MAX_TOKENS = 500;
const TOPE_ANONIMO = 30; // preguntas totales para quien no tiene plan Pro IA activo

async function revisarAnonimo(id) {
  // Sin almacen o sin id de dispositivo, no hay forma honesta de contar --
  // no se bloquea (mejor eso a inventar un conteo), pero queda documentado.
  if (!almacenConfigurado() || !id) return { permitido: true, sinConteo: true };
  const k = "anon:" + String(id).slice(0, 80);
  const actual = (await kvGet(k)) || { usadas: 0 };
  if (actual.usadas >= TOPE_ANONIMO) return { permitido: false };
  actual.usadas += 1;
  await kvSet(k, actual);
  return { permitido: true, restantes: TOPE_ANONIMO - actual.usadas };
}

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
  const email = String(body.email || "").trim().toLowerCase();
  const clave = String(body.clave || "").trim();
  const dispositivo = String(body.dispositivo || "").trim();
  if (!pregunta) return res.status(400).json({ error: "sin_pregunta" });

  // Si mandan email+clave tienen que ser una licencia REAL: si no valida, no
  // se sigue de largo (podria ser alguien probando datos inventados).
  const dijoTenerLicencia = Boolean(email && clave);
  if (dijoTenerLicencia && !claveValida(email, clave)) {
    return res.status(403).json({ error: "licencia_invalida" });
  }

  let modo = "demo"; // "creditos" | "demo"
  if (dijoTenerLicencia) {
    const saldo = await revisarSaldo(email);
    if (saldo.activo) {
      modo = "creditos";
    } else if (saldo.motivo === "saldo_agotado") {
      return res.status(429).json({
        error: "saldo_agotado",
        mensaje: "Se acabaron tus créditos de IA. Recargá desde la app para seguir usando el asistente compartido, o seguí usando el asistente local mientras tanto.",
      });
    }
    // "sin_cuenta" / "almacen_no_configurado": esta licencia es real pero
    // todavia no tiene saldo de creditos -> cae al tope generico de abajo
    // en vez de cortar de golpe (no deberia pasar en el flujo normal, ya que
    // toda licencia nueva recibe el bono de bienvenida al mintearse — ver
    // api/licencia.js — pero es una red de seguridad honesta si por lo que
    // sea no lo tiene).
  }

  if (modo === "demo") {
    const chequeo = await revisarAnonimo(dispositivo || email);
    if (!chequeo.permitido) {
      return res.status(429).json({
        error: "tope_alcanzado",
        mensaje: "Llegaste al límite de preguntas gratis. Con el plan Pro IA tenés cuota mensual completa incluida.",
      });
    }
  }

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
    if (modo === "creditos" && data.usage) {
      // Esperar el descuento ANTES de responder: en serverless la funcion
      // puede congelarse apenas se manda la respuesta, y un descuento "fire
      // and forget" se perderia silenciosamente -- exactamente el uso que no
      // se quiere regalar gratis.
      const tokens = (data.usage.input_tokens || 0) + (data.usage.output_tokens || 0);
      try { await descontarCreditos(email, tokens); } catch (e) { /* almacen caido: no rompe la respuesta ya generada */ }
    }
    return res.status(200).json({ texto: texto || "" });
  } catch (e) {
    return res.status(502).json({ error: "fetch_fail" });
  }
}
