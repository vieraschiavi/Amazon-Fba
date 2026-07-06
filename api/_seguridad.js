// api/_seguridad.js — Guardas anti-abuso compartidas por los endpoints que
// cuestan plata real (Claude, Keepa, MercadoPago). El prefijo "_" hace que
// Vercel NO trate este archivo como una ruta (no es un endpoint).
//
// Dos capas, cada una con su límite HONESTO (ninguna reemplaza a la otra):
//
// 1) CORS restringido al propio sitio (origenPermitido/aplicarCors): evita
//    que OTRO sitio web haga que el NAVEGADOR de un visitante llame a estos
//    endpoints en tu nombre. Esto NO detiene un bot/script que llama directo
//    (curl, Python, etc.): CORS solo lo aplica el navegador, nunca un
//    cliente HTTP arbitrario — por eso no alcanza solo con esto.
// 2) Header de aplicación (clienteValido): el JS del sitio lo manda siempre;
//    un bot genérico que escanea rutas /api/* comunes en internet no lo
//    conoce y queda afuera. NO es un secreto (se ve en el código fuente de
//    la página): filtra ruido de bots masivos y escaneo automático, no a
//    alguien que lea el JS del sitio a propósito.
//
// Para protección real contra tráfico automatizado DIRIGIDO, la capa que
// corresponde es el Firewall de Vercel (Attack Challenge Mode — gratis en
// todos los planes, se activa en el dashboard del proyecto → Firewall →
// Rules). Estas dos capas de acá son un complemento de código, no un
// reemplazo de eso.

const ORIGENES_OK = /^https:\/\/amazon-fba-[a-z0-9-]+\.vercel\.app$/;
// Cuando se conecte un dominio propio (ver README, "Landing web y dominio
// propio"), agregarlo acá, ej: /^https:\/\/(www\.)?tudominio\.com$/
export const APP_HEADER = "x-mv-app";
const APP_TOKEN = "mvfba-web-1";

export function aplicarCors(req, res, metodos) {
  const origin = req.headers.origin || "";
  const ok = ORIGENES_OK.test(origin);
  res.setHeader("Access-Control-Allow-Origin", ok ? origin : "https://amazon-fba-seven.vercel.app");
  res.setHeader("Access-Control-Allow-Headers", "Content-Type, " + APP_HEADER);
  res.setHeader("Access-Control-Allow-Methods", metodos);
  res.setHeader("Vary", "Origin");
}

export function clienteValido(req) {
  return req.headers[APP_HEADER] === APP_TOKEN;
}
