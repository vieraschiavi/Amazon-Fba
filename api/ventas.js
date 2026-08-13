// © 2026 Martín Viera. Todos los derechos reservados.
// api/ventas.js — Reporte de atribucion: cuantas ventas y cuanto facturo cada
// plan/canal (utm_source), para comparar contra el esfuerzo de redes
// sociales que se invierte en cada uno de los proyectos.
//
// Endpoint de administracion, NO publico: exige el header "x-admin-secret"
// igual a la variable de entorno ADMIN_SECRET. Sin esa variable configurada,
// responde 503 (mismo patron honesto que el resto del sistema: sin la pieza
// que hace falta, la funcion no esta disponible en vez de fallar raro).
import crypto from "crypto";
import { ultimasVentas } from "./_atribucion.js";
import { limitarPorIp } from "./_seguridad.js";

// Comparacion en tiempo constante: "!==" corta apenas encuentra la primera
// diferencia, asi que el tiempo de respuesta varia segun cuantos caracteres
// iniciales acertó quien pregunta -- una filtracion de timing teorica que
// timingSafeEqual no tiene (necesita buffers del MISMO largo, por eso el
// chequeo de longitud primero, que no filtra nada mas alla de "no es del
// mismo largo").
function compararSeguro(a, b) {
  const bufA = Buffer.from(String(a));
  const bufB = Buffer.from(String(b));
  return bufA.length === bufB.length && crypto.timingSafeEqual(bufA, bufB);
}

export default async function handler(req, res) {
  if (req.method !== "GET") return res.status(405).json({ error: "method" });

  const secreto = process.env.ADMIN_SECRET;
  if (!secreto) return res.status(503).json({ error: "admin_no_configurado" });

  // Sin esto, alguien podia probar valores de x-admin-secret sin ningun
  // freno de velocidad.
  const limite = await limitarPorIp(req, "ventas-admin", 20, 3600);
  if (!limite.permitido) return res.status(429).json({ error: "demasiados_intentos" });

  if (!compararSeguro(req.headers["x-admin-secret"] || "", secreto)) {
    return res.status(403).json({ error: "no_autorizado" });
  }

  const cantidad = Math.min(1000, Math.max(1, Number(req.query && req.query.n) || 200));
  let ventas;
  try {
    ventas = await ultimasVentas(cantidad);
  } catch (e) {
    return res.status(503).json({ error: "almacen_no_configurado" });
  }

  const porCanal = {};
  const porPlan = {};
  let totalUsd = 0;
  for (const v of ventas) {
    const fuente = (v.utm && v.utm.utm_source) || "(sin_utm)";
    porCanal[fuente] = porCanal[fuente] || { ventas: 0, monto: 0 };
    porCanal[fuente].ventas += 1;
    porCanal[fuente].monto += Number(v.monto) || 0;

    porPlan[v.plan || "(sin_plan)"] = (porPlan[v.plan || "(sin_plan)"] || 0) + 1;
    totalUsd += Number(v.monto) || 0;
  }

  return res.status(200).json({
    totalVentas: ventas.length,
    totalUsd: Math.round(totalUsd * 100) / 100,
    porCanal,
    porPlan,
    ventas,
  });
}
