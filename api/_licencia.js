// © 2026 Martín Viera. Todos los derechos reservados.
// api/_licencia.js — Formula HMAC de licencia, compartida por licencia.js,
// validar.js e ia.js (antes estaba triplicada; con la cuota de IA en juego,
// un desvio entre copias podria dejar pasar a alguien sin licencia real).
// El prefijo "_" hace que Vercel NO trate este archivo como una ruta.
import crypto from "crypto";

export const SECRETO = process.env.LICENCIA_SECRETO || "mv-amazon-fba-2026-clave-de-firma";
// Identificador interno, invisible para el usuario. Se deja SIN TOCAR aunque
// el nombre comercial paso a ser "MV FBA IA": cambiarlo invalidaria las
// licencias ya emitidas a clientes que ya pagaron.
export const DOMINIO = "MV-Amazon-Fba";

export function generarClave(email) {
  const base = String(email || "").trim().toLowerCase() + DOMINIO;
  const hex = crypto.createHmac("sha256", SECRETO).update(base).digest("hex").toUpperCase().slice(0, 16);
  return "MVFBA-" + [hex.slice(0, 4), hex.slice(4, 8), hex.slice(8, 12), hex.slice(12, 16)].join("-");
}

export function claveValida(email, clave) {
  const limpia = String(clave || "").trim().toUpperCase();
  return Boolean(email) && Boolean(limpia) && limpia === generarClave(email);
}
