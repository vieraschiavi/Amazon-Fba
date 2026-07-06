// api/mercado.js — Búsqueda REAL de productos por API (Keepa) para el demo web.
//
// Los datos reales de mercado NO vienen de un modelo de IA (Claude/ChatGPT/Gemini
// inventarían números): vienen de una API de datos. Keepa rastrea el historial de
// precio y ranking (BSR) de millones de productos de Amazon. Este endpoint es un
// proxy: la clave de Keepa no puede llamarse directo desde el navegador (CORS +
// no exponer la clave), así que el cliente la manda acá y nosotros consultamos.
//
// La clave puede venir del visitante (BYOK, body.keepaKey) o del dueño del demo
// (env KEEPA_API_KEY, para que se vean datos reales sin clave propia). Sin ninguna
// de las dos -> 503 y el cliente cae al EJEMPLO claramente etiquetado.
//
// HONESTIDAD: Keepa da BSR, no ventas exactas. ventas_estim es una estimación por
// curva BSR->ventas (gruesa), igual que en el programa de PC (data/keepa.py).

import { aplicarCors, clienteValido } from "./_seguridad.js";

const DOMAIN = 1; // amazon.com (US)
const UA = "mv-amazon-fba-ia/1.0";

// Curva BSR -> ventas/mes (aprox, Home & Kitchen US). Interpolada en log10.
const CURVA = [[100, 9000], [500, 3000], [1000, 1800], [5000, 500],
  [10000, 230], [50000, 45], [100000, 18], [500000, 3]];
function estimVentas(bsr) {
  if (!bsr || bsr <= 0) return 0;
  if (bsr <= CURVA[0][0]) return CURVA[0][1];
  if (bsr >= CURVA[CURVA.length - 1][0]) return CURVA[CURVA.length - 1][1];
  for (let i = 0; i < CURVA.length - 1; i++) {
    const [b1, v1] = CURVA[i], [b2, v2] = CURVA[i + 1];
    if (b1 <= bsr && bsr <= b2) {
      const t = (Math.log10(bsr) - Math.log10(b1)) / (Math.log10(b2) - Math.log10(b1));
      return Math.round(v1 * Math.pow(v2 / v1, t));
    }
  }
  return 0;
}

export default async function handler(req, res) {
  aplicarCors(req, res, "POST, OPTIONS");
  if (req.method === "OPTIONS") return res.status(204).end();
  if (req.method !== "POST") return res.status(405).json({ error: "method" });
  if (!clienteValido(req)) return res.status(403).json({ error: "cliente_no_reconocido" });

  let body = req.body;
  if (typeof body === "string") { try { body = JSON.parse(body); } catch (e) { body = {}; } }
  body = body || {};
  const keyword = String(body.keyword || "").slice(0, 120).trim();
  const min = Math.max(0, Number(body.min) || 0);
  const max = Math.max(min + 1, Number(body.max) || 100);
  const key = String(body.keepaKey || "").trim() || process.env.KEEPA_API_KEY;

  if (!key) return res.status(503).json({ ok: false, error: "sin_clave_keepa" });
  if (keyword.length < 3) return res.status(400).json({ ok: false, error: "keyword_corta" });

  try {
    // 1) Product Finder -> lista de ASIN con ranking de ventas real.
    const seleccion = {
      title: keyword,
      current_NEW_gte: Math.round(min * 100),
      current_NEW_lte: Math.round(max * 100),
      current_SALES_gte: 1,
      sort: [["current_SALES", "asc"]],
      productType: [0, 1],
      perPage: 20,
      page: 0,
    };
    const qUrl = `https://api.keepa.com/query?key=${encodeURIComponent(key)}&domain=${DOMAIN}`;
    const qResp = await fetch(qUrl, {
      method: "POST",
      headers: { "User-Agent": UA, "Content-Type": "application/json" },
      body: JSON.stringify(seleccion),
    });
    if (!qResp.ok) {
      const code = qResp.status;
      const det = [400, 401, 402, 403].includes(code) ? "clave_invalida_o_sin_tokens" : ("http_" + code);
      return res.status(502).json({ ok: false, error: det });
    }
    const qData = await qResp.json();
    const asins = (qData.asinList || []).slice(0, 10);
    if (!asins.length) return res.status(200).json({ ok: false, error: "sin_resultados", productos: [] });

    // 2) Detalle de esos ASIN (precio, BSR, rating, reseñas).
    const pUrl = `https://api.keepa.com/product?key=${encodeURIComponent(key)}`
      + `&domain=${DOMAIN}&asin=${asins.join(",")}&stats=90&rating=1`;
    const pResp = await fetch(pUrl, { headers: { "User-Agent": UA } });
    if (!pResp.ok) return res.status(502).json({ ok: false, error: "http_" + pResp.status });
    const pData = await pResp.json();

    const productos = [];
    for (const p of pData.products || []) {
      const cur = (p.stats && p.stats.current) || [];
      const val = (idx, div) => (cur.length > idx && cur[idx] != null && cur[idx] >= 0)
        ? cur[idx] / (div || 1) : null;
      const precio = val(1, 100) || val(0, 100);   // NEW, si no AMAZON (USD)
      const bsr = val(3);                            // SALES rank
      const rating = val(16, 10);                    // 0-50 -> 0-5
      const resenas = val(17);                       // COUNT_REVIEWS
      const asin = p.asin || "";
      productos.push({
        asin,
        titulo: (p.title || "").slice(0, 120),
        precio: precio ? Math.round(precio * 100) / 100 : null,
        bsr: bsr ? Math.round(bsr) : null,
        ventas_estim: bsr ? estimVentas(Math.round(bsr)) : 0,
        rating: rating ? Math.round(rating * 10) / 10 : null,
        resenas: resenas ? Math.round(resenas) : 0,
        link: asin ? `https://www.amazon.com/dp/${asin}` : "",
      });
    }
    productos.sort((a, b) => (a.bsr || 1e9) - (b.bsr || 1e9));
    return res.status(200).json({ ok: productos.length > 0, fuente: "Keepa", productos });
  } catch (e) {
    return res.status(502).json({ ok: false, error: "fetch_fail" });
  }
}
