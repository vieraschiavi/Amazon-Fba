// api/creditos.js — Deja que un cliente con licencia vea su saldo de
// creditos de IA (ver api/_creditosia.js). Requiere {email, clave} de una
// licencia REAL -- nunca expone el saldo de otra persona.
//
// Reemplaza a api/cuota.js (que exponia la cuota mensual fija del viejo plan
// "Pro IA"): los creditos no vencen ni tienen "modo" que elegir, asi que solo
// hace falta consultar el saldo.
//
// El branch POST de aca abajo es api/demo-registro.js fusionado en este mismo
// archivo (vercel.json tiene el rewrite /api/demo-registro -> /api/creditos,
// asi que la URL que llaman mobile/js/licencia.js y core/licencia.py no
// cambia). La fusion es SOLO para bajar de 13 a 12 archivos publicos en api/:
// el plan Hobby de Vercel limita a 12 Serverless Functions por deployment, y
// sumar api/resenas.js hizo que el deploy fallara. GET y POST no se pisan
// (metodos distintos), asi que cada uno mantiene su propia logica de CORS
// intacta.
import { aplicarCors, clienteValido, limitarPorIp } from "./_seguridad.js";
import { claveValida } from "./_licencia.js";
import { revisarSaldo } from "./_creditosia.js";
import { registrarDemo } from "./_demo.js";

export default async function handler(req, res) {
  const metodoPedido = String(req.headers["access-control-request-method"] || req.method || "").toUpperCase();

  if (req.method === "POST" || (req.method === "OPTIONS" && metodoPedido === "POST")) {
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

    // Esta rama no tiene clienteValido (CORS abierto a * a proposito: la
    // llaman apps nativas sin Origin/header consistente). Sin ningun freno,
    // cualquiera podia spamear emails ajenos/inventados -- y el cron de
    // recordatorio despues les manda un mail real de "tu demo vence manana"
    // a gente que nunca la pidio (reputacion de envio del dominio). 5/hora
    // por IP alcanza de sobra para un uso legitimo.
    const limite = await limitarPorIp(req, "demoreg", 5, 3600);
    if (!limite.permitido) return res.status(200).json({ ok: false });

    try {
      await registrarDemo(nombre, email);
    } catch (e) { /* almacen no configurado: no bloquea, no rompe la demo */ }
    return res.status(200).json({ ok: true });
  }

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
