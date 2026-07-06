// api/cuota.js — Deja que un cliente con plan "Pro IA" vea su cuota y elija
// como manejarla: "topear" (se resetea cada mes) o "acumular" (lo que no usa
// se suma al mes siguiente, con un tope). Requiere {email, clave} de una
// licencia REAL — nunca expone ni modifica la cuota de otra persona.
import { aplicarCors, clienteValido } from "./_seguridad.js";
import { claveValida } from "./_licencia.js";
import { revisarCuota, fijarModoCuota } from "./_cuotaia.js";

export default async function handler(req, res) {
  aplicarCors(req, res, "GET, POST, OPTIONS");
  if (req.method === "OPTIONS") return res.status(204).end();
  if (!clienteValido(req)) return res.status(403).json({ error: "cliente_no_reconocido" });

  let body = req.body;
  if (typeof body === "string") { try { body = JSON.parse(body); } catch (e) { body = {}; } }
  body = body || {};
  const q = req.query || {};
  const email = String(body.email || q.email || "").trim().toLowerCase();
  const clave = String(body.clave || q.clave || "").trim();
  if (!claveValida(email, clave)) {
    return res.status(403).json({ error: "licencia_invalida" });
  }

  if (req.method === "GET") {
    const cuota = await revisarCuota(email);
    return res.status(200).json(cuota);
  }
  if (req.method === "POST") {
    const modo = String(body.modo || "");
    if (modo !== "topear" && modo !== "acumular") {
      return res.status(400).json({ error: "modo_invalido" });
    }
    const registro = await fijarModoCuota(email, modo);
    return res.status(200).json({ ok: true, registro });
  }
  return res.status(405).json({ error: "method" });
}
