// © 2026 Martín Viera. Todos los derechos reservados.
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
import { almacenConfigurado, kvGet, kvSet } from "./_almacen.js";

// Dominio propio (mvfbaia.com, conectado al proyecto de Vercel) + los
// previews *.vercel.app del mismo proyecto.
const ORIGENES_OK = /^https:\/\/((www\.)?mvfbaia\.com|amazon-fba-[a-z0-9-]+\.vercel\.app)$/;
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

// Vercel corre detras de su propio proxy: el IP real del visitante llega en
// x-forwarded-for (el primero de la lista, si hay varios proxies en cadena).
export function ipDeRequest(req) {
  const fwd = req.headers["x-forwarded-for"];
  if (fwd) return String(fwd).split(",")[0].trim();
  return (req.socket && req.socket.remoteAddress) || "desconocida";
}

// Limite de intentos por IP en una ventana de tiempo. Pensado para lo que
// CORS y clienteValido NO frenan: un script que llama directo al endpoint
// (curl, Python) probando muchos valores seguidos -- enumerar payment_id
// ajenos en api/licencia.js, o gastar sin limite la clave de Claude/Keepa del
// dueño en api/ia.js y api/mercado.js cuando el que llama no manda un
// identificador propio (dispositivo vacio, o key propia vacia).
//
// Sin almacen configurado no hay forma honesta de contar -> no bloquea
// (mismo criterio que revisarAnonimo en api/ia.js: mejor eso que inventar un
// conteo). Queda documentado, no es un fallback silencioso.
export async function limitarPorIp(req, prefijo, tope, ventanaSeg) {
  if (!almacenConfigurado()) return { permitido: true, sinConteo: true };
  const clave = prefijo + ":" + ipDeRequest(req);
  const actual = (await kvGet(clave)) || { usos: 0 };
  if (actual.usos >= tope) return { permitido: false };
  actual.usos += 1;
  await kvSet(clave, actual, ventanaSeg);
  return { permitido: true, restantes: tope - actual.usos };
}
