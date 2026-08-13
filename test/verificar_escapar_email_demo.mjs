// © 2026 Martín Viera. Todos los derechos reservados.
/* verificar_escapar_email_demo.mjs — el "nombre" de un registro de demo no
 * puede inyectar HTML en el email de recordatorio.
 *
 * POR QUE EXISTE: POST /api/creditos (registro de demo) acepta {email,
 * nombre} sin verificar que quien llama sea el dueño de ese email -- solo
 * "email.includes('@')" + limite de 5/hora por IP. Un dia despues,
 * api/cron-recordatorio-demo.js interpolaba `nombre` CRUDO en el HTML de un
 * mail real, firmado por el dominio legitimo (Resend). Un atacante podia
 * registrar el email de la VICTIMA con un `nombre` que en realidad es un
 * link/HTML de phishing, y ese phishing salia con reputacion de envio
 * genuina. Ahora _email.js expone escaparHtml() y cron-recordatorio-demo.js
 * la usa antes de armar el saludo.
 *
 * Uso:   node test/verificar_escapar_email_demo.mjs
 */
import fs from "node:fs";
import path from "node:path";

const RAIZ = path.join(import.meta.dirname, "..");
let fallas = 0;
const ok = (m) => console.log("OK     " + m);
const falla = (m) => { fallas++; console.error("FALLA  " + m); };

const { escaparHtml } = await import("../api/_email.js");

// --- escaparHtml() en si misma ---
const CASOS = [
  ["<script>alert(1)</script>", "&lt;script&gt;alert(1)&lt;/script&gt;"],
  ['<a href="javascript:x">y</a>', "&lt;a href=&quot;javascript:x&quot;&gt;y&lt;/a&gt;"],
  ["O'Brien & Cía", "O&#39;Brien &amp; Cía"],
  ["", ""],
  [null, ""],
  [undefined, ""],
];
for (const [entrada, esperado] of CASOS) {
  const salida = escaparHtml(entrada);
  if (salida === esperado) ok(`escaparHtml(${JSON.stringify(entrada)}) -> ${JSON.stringify(salida)}`);
  else falla(`escaparHtml(${JSON.stringify(entrada)}) dio ${JSON.stringify(salida)}, se esperaba ${JSON.stringify(esperado)}`);
}
// ningun caracter peligroso sobrevive TAL CUAL (comparar contra el original
// sin tocar, no contra si el resultado "contiene" el caracter -- la propia
// forma escapada de "&" es "&amp;", que por supuesto contiene "&")
for (const c of ["<", ">", '"', "'", "&"]) {
  const entrada = `x${c}y`;
  if (escaparHtml(entrada) !== entrada) ok(`  el caracter "${c}" queda escapado`);
  else falla(`el caracter "${c}" NO quedo escapado`);
}

// --- cron-recordatorio-demo.js usa escaparHtml antes de armar el saludo ---
{
  const SRC = fs.readFileSync(path.join(RAIZ, "api/cron-recordatorio-demo.js"), "utf8");
  const codigo = SRC.split("\n").filter((l) => !l.trim().startsWith("//")).join("\n");
  if (/import\s*\{[^}]*escaparHtml[^}]*\}\s*from\s*["']\.\/_email\.js["']/.test(codigo))
    ok("cron-recordatorio-demo.js importa escaparHtml");
  else falla("cron-recordatorio-demo.js no importa escaparHtml");

  const idxEscapar = codigo.indexOf("escaparHtml(nombre)");
  const idxSaludo = codigo.indexOf("saludo");
  if (idxEscapar !== -1 && idxEscapar < idxSaludo)
    ok("  se escapa ANTES de armar el saludo (no queda una segunda interpolacion cruda)");
  else falla("no se pudo confirmar que el escape corra antes de armar el saludo");

  // no puede quedar NINGUNA interpolacion directa de `nombre` sin pasar por
  // escaparHtml -- solo debe aparecer del lado derecho de "= escaparHtml(nombre)"
  const usosDeNombre = [...codigo.matchAll(/\$\{[^}]*\bnombre\b[^}]*\}/g)].map((m) => m[0]);
  const crudos = usosDeNombre.filter((u) => !/escaparHtml/.test(u));
  if (crudos.length === 0) ok("  ninguna interpolacion de `nombre` queda sin pasar por escaparHtml");
  else falla(`quedan interpolaciones crudas de nombre: ${crudos.join(", ")}`);
}

console.log("");
if (fallas) {
  console.error(`FALLO: ${fallas} problema(s) en el escape del email de recordatorio.`);
  process.exit(1);
}
console.log("OK: escaparHtml() cubre los 5 caracteres peligrosos y cron-recordatorio-demo.js la usa antes de armar el mail.");
