// © 2026 Martín Viera. Todos los derechos reservados.
// api/_resenas.js — Reseñas de compradores REALES (puntaje 1-5 + comentario),
// guardadas en el mismo almacen (Vercel KV/Upstash) que ya usa el saldo de
// creditos y el registro de demos. Una reseña por payment_id (idempotente):
// nadie puede mandar la "reseña" del mismo pago dos veces para inflar el
// promedio -- la verificacion de que el pago es real y aprobado la hace
// api/resenas.js ANTES de llamar aca (mismo criterio que api/reembolso.js).
//
// Sin almacen configurado, listarResenas/resumenResenas devuelven vacio de
// forma honesta -- la landing muestra "sé el primero en dejar tu reseña" en
// vez de inventar numeros. Nunca se fabrica una reseña ni un promedio falso.
import { almacenConfigurado, kvGet, kvSet, kvPush, kvRango } from "./_almacen.js";

const MAX_INDICE = 500;

function claveResena(paymentId) {
  return "resena:" + String(paymentId || "").trim();
}

export async function agregarResenaSiNueva({ paymentId, nombre, puntaje, comentario, plan }) {
  if (!almacenConfigurado() || !paymentId) return null;
  const k = claveResena(paymentId);
  const ya = await kvGet(k);
  if (ya) return null;
  const registro = { nombre, puntaje, comentario, plan, fecha: new Date().toISOString() };
  await kvSet(k, registro);
  await kvPush("resenas:indice", paymentId, MAX_INDICE);
  return registro;
}

export async function listarResenas(cantidad = 20) {
  if (!almacenConfigurado()) return [];
  const ids = await kvRango("resenas:indice", 0, Math.max(0, cantidad - 1));
  const regs = await Promise.all(ids.map((id) => kvGet(claveResena(id))));
  return regs.filter(Boolean);
}

export async function resumenResenas() {
  if (!almacenConfigurado()) return { promedio: 0, total: 0 };
  const ids = await kvRango("resenas:indice", 0, MAX_INDICE - 1);
  const regs = (await Promise.all(ids.map((id) => kvGet(claveResena(id))))).filter(Boolean);
  if (!regs.length) return { promedio: 0, total: 0 };
  const suma = regs.reduce((acc, r) => acc + (r.puntaje || 0), 0);
  return { promedio: Math.round((suma / regs.length) * 10) / 10, total: regs.length };
}
