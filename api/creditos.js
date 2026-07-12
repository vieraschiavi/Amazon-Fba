// api/creditos.js — Deja que un cliente con licencia vea su saldo de
// creditos de IA (ver api/_creditosia.js). Requiere {email, clave} de una
// licencia REAL -- nunca expone el saldo de otra persona.
//
// Reemplaza a api/cuota.js (que exponia la cuota mensual fija del viejo plan
// "Pro IA"): los creditos no vencen ni tienen "modo" que elegir, asi que solo
// hace falta consultar el saldo.
import { aplicarCors, clienteValido } from "./_seguridad.js";
import { claveValida } from "./_licencia.js";
import { revisarSaldo } from "./_creditosia.js";

export default async function handler(req, res) {
  aplicarCors(req, res, "GET, OPTIONS");
  if (req.method === "OPTIONS") return res.status(204).end();
  if (req.method !== "GET") return res.status(405).json({ error: "method" });
  if (!clienteValido(req)) return res.status(403).json({ error: "cliente_no_reconocido" });

  const q = req.query || {};
  const email = String(q.email || "").trim().toLowerCase();
  const clave = String(q.clave || "").trim();
  if (!claveValida(email, clave)) {
    return res.status(403).json({ error: "licencia_invalida" });
  }

  // claveValida ya paso: si esta licencia es anterior al sistema de creditos
  // (sin registro), el segundo argumento hace que reciba su bono de
  // bienvenida aca mismo -- el cliente viejo ve creditos apenas abre Config.
  const saldo = await revisarSaldo(email, true);
  return res.status(200).json(saldo);
}
