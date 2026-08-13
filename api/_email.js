// © 2026 Martín Viera. Todos los derechos reservados.
// api/_email.js — Cliente minimo (fetch puro, sin SDK) para Resend, usado
// SOLO para el recordatorio de "tu demo vence mañana" (api/cron-recordatorio-demo.js).
// El prefijo "_" hace que Vercel NO trate este archivo como una ruta.
//
// Variable de entorno esperada: RESEND_API_KEY (se consigue gratis en
// resend.com, sin tarjeta para el plan free). RESEND_FROM es opcional: sin
// verificar un dominio propio en Resend, se puede mandar desde
// "onboarding@resend.dev" (limitado, sirve para arrancar).
//
// Si no esta configurado, emailConfigurado() devuelve false y quien llame a
// enviarEmail() debe tratarlo como no-op -- mismo patron honesto que el
// resto del sistema (PayPal, KV): sin la pieza que hace falta, la funcion
// simplemente no esta disponible, nunca rompe el resto del sitio.
const API_KEY = process.env.RESEND_API_KEY;
const FROM = process.env.RESEND_FROM || "MV FBA IA <onboarding@resend.dev>";

export function emailConfigurado() {
  return Boolean(API_KEY);
}

// Escapa texto de USUARIO antes de interpolarlo en el HTML de un email.
// Server-side no hay `document` (a diferencia de landing/gracias.html y
// mobile/js/seguro.js, que escapan armando un <div> y leyendo su
// innerHTML) -- por eso esta version es manual, pero cubre los mismos 5
// caracteres. Sin esto, un campo como "nombre" (que el propio visitante
// carga sin verificacion de que sea realmente el dueño del email) viajaba
// crudo al HTML de un mail que sale FIRMADO por el dominio real: inyeccion
// de HTML/links en un email con reputacion de envio legitima.
export function escaparHtml(s) {
  return String(s ?? "").replace(/[&<>"']/g, (c) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
  }[c]));
}

export async function enviarEmail({ to, subject, html }) {
  if (!emailConfigurado()) return null;
  const r = await fetch("https://api.resend.com/emails", {
    method: "POST",
    headers: { Authorization: `Bearer ${API_KEY}`, "Content-Type": "application/json" },
    body: JSON.stringify({ from: FROM, to, subject, html }),
  });
  const d = await r.json().catch(() => ({}));
  if (!r.ok) throw new Error("resend_error: " + JSON.stringify(d));
  return d;
}
