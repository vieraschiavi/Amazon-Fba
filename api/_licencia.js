// © 2026 Martín Viera. Todos los derechos reservados.
// api/_licencia.js — Formula HMAC de licencia, compartida por licencia.js,
// validar.js e ia.js (antes estaba triplicada; con la cuota de IA en juego,
// un desvio entre copias podria dejar pasar a alguien sin licencia real).
// El prefijo "_" hace que Vercel NO trate este archivo como una ruta.
import crypto from "crypto";

// SIN fallback a proposito. Antes, si LICENCIA_SECRETO no estaba seteada en
// algun entorno (un Preview, un branch nuevo, un typo en el nombre de la
// variable) el codigo fallaba ABIERTO con un secreto fijo escrito ac
// mismo -- cualquiera que leyera este archivo podia calcular una licencia
// Pro valida para CUALQUIER email, gratis, sin dejar rastro de pago. Ahora,
// sin la variable configurada, SECRETO_CONFIGURADO da false y todo el
// sistema de licencias falla cerrado (mismo patron que MP_ACCESS_TOKEN,
// RESEND_API_KEY y ADMIN_SECRET en el resto de api/*.js).
export const SECRETO = process.env.LICENCIA_SECRETO || "";
export const SECRETO_CONFIGURADO = Boolean(SECRETO);
// Identificador interno, invisible para el usuario. Se deja SIN TOCAR aunque
// el nombre comercial paso a ser "MV FBA IA": cambiarlo invalidaria las
// licencias ya emitidas a clientes que ya pagaron.
export const DOMINIO = "MV-Amazon-Fba";

export function generarClave(email) {
  if (!SECRETO_CONFIGURADO) {
    // No emitir una clave calculada con un secreto vacio: quedaria
    // permanentemente invalida el dia que se configure el secreto real, y
    // el cliente que pago se quedaria con una "licencia" que nunca prendio.
    throw new Error("LICENCIA_SECRETO no configurado");
  }
  const base = String(email || "").trim().toLowerCase() + DOMINIO;
  const hex = crypto.createHmac("sha256", SECRETO).update(base).digest("hex").toUpperCase().slice(0, 16);
  return "MVFBA-" + [hex.slice(0, 4), hex.slice(4, 8), hex.slice(8, 12), hex.slice(12, 16)].join("-");
}

export function claveValida(email, clave) {
  if (!SECRETO_CONFIGURADO) return false;   // falla cerrado: sin secreto, ninguna clave es valida
  const limpia = String(clave || "").trim().toUpperCase();
  return Boolean(email) && Boolean(limpia) && limpia === generarClave(email);
}
