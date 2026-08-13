// © 2026 Martín Viera. Todos los derechos reservados.
/* verificar_owner_github.mjs — La licencia de dueño se autoriza probando
 * acceso al repo PRIVADO, y no de otra forma.
 *
 * POR QUE EXISTE: el camino ?dueno=1 emite una licencia Pro gratis. Si se
 * autorizara mal, cualquiera deja de pagar el producto. Las trampas concretas
 * que este test fija:
 *
 *   - un token que da 200 sobre OTRO repo no sirve (si el repo se tomara del
 *     request, cualquiera apuntaria a uno suyo y entraria);
 *   - sobre un repo PUBLICO, poder LEERLO no sirve como prueba (lo lee
 *     cualquiera, hasta sin token): ahi hace falta permiso de ESCRITURA, que
 *     es el mismo grupo de gente que puede correr el workflow;
 *   - sin token, con token vacio, o si GitHub falla, NO autoriza (falla cerrado).
 *
 * Uso:   node test/verificar_owner_github.mjs
 */
import assert from "node:assert";
import { accesoAlRepoValido } from "../api/_owner_github.js";

let fallas = 0;
function comprobar(desc, cond) {
  if (cond) { console.log("OK     " + desc); }
  else { console.log("FALLA  " + desc); fallas++; }
}

// Simula la API de GitHub: responde segun el token que le llegue.
function githubFalso(porToken) {
  return async (url, opciones) => {
    const auth = String((opciones && opciones.headers && opciones.headers.authorization) || "");
    const token = auth.replace(/^Bearer\s+/i, "");
    const r = porToken[token];
    if (!r) return { ok: false, status: 404, json: async () => ({}) };
    if (r.lanzar) throw new Error("red caida");
    return { ok: true, status: 200, json: async () => r };
  };
}

const REPO = "vieraschiavi/Amazon-Fba";

// --- el caso bueno: token del workflow, repo correcto y privado ---
{
  const gh = githubFalso({ "token-del-workflow": { full_name: REPO, private: true } });
  comprobar("un token con acceso al repo privado SI autoriza",
    (await accesoAlRepoValido("token-del-workflow", gh)) === true);
}

// --- token que solo puede leer OTRO repo ---
{
  const gh = githubFalso({ "token-ajeno": { full_name: "otro/repo", private: true } });
  comprobar("un token de OTRO repo no autoriza (aunque GitHub responda 200)",
    (await accesoAlRepoValido("token-ajeno", gh)) === false);
}

// --- repo PUBLICO: leerlo no prueba nada, lo lee cualquiera ---
// Este es el caso del curioso que se hace un token propio y prueba el endpoint:
// GitHub le contesta 200 sobre el repo publico, pero con pull y nada mas.
{
  const gh = githubFalso({ "token-de-un-curioso": {
    full_name: REPO, private: false,
    permissions: { admin: false, maintain: false, push: false, triage: false, pull: true },
  } });
  comprobar("repo PUBLICO + solo lectura NO autoriza (leerlo no prueba nada)",
    (await accesoAlRepoValido("token-de-un-curioso", gh)) === false);
}

// --- repo PUBLICO pero con acceso de ESCRITURA: ese si es el dueño ---
// Es el caso del GITHUB_TOKEN del workflow (corre con contents:write) y el del
// dueño con su propio token. Mismo grupo que puede correr el workflow.
for (const [rol, permisos] of [
  ["push",     { admin: false, maintain: false, push: true,  pull: true }],
  ["maintain", { admin: false, maintain: true,  push: false, pull: true }],
  ["admin",    { admin: true,  maintain: false, push: false, pull: true }],
]) {
  const gh = githubFalso({ "token-con-escritura": { full_name: REPO, private: false, permissions: permisos } });
  comprobar(`repo PUBLICO + permiso "${rol}" SI autoriza (solo lo tiene quien puede correr el workflow)`,
    (await accesoAlRepoValido("token-con-escritura", gh)) === true);
}

// --- repo publico y GitHub ni siquiera manda "permissions" ---
// Pasa en llamadas sin autenticar. Sin dato, no se asume nada: falla cerrado.
{
  const gh = githubFalso({ "token-raro": { full_name: REPO, private: false } });
  comprobar("repo PUBLICO sin campo permissions NO autoriza (no se asume nada)",
    (await accesoAlRepoValido("token-raro", gh)) === false);
}

// --- el repo PRIVADO sigue autorizando por sola lectura ---
// Ahi leerlo SI prueba acceso: nadie mas que un colaborador puede.
{
  const gh = githubFalso({ "token-lector-privado": {
    full_name: REPO, private: true,
    permissions: { admin: false, maintain: false, push: false, pull: true },
  } });
  comprobar("repo PRIVADO + solo lectura SI autoriza (nadie mas puede leerlo)",
    (await accesoAlRepoValido("token-lector-privado", gh)) === true);
}

// --- y un repo AJENO no entra ni con permisos de admin ---
{
  const gh = githubFalso({ "token-admin-ajeno": {
    full_name: "otro/repo", private: false,
    permissions: { admin: true, maintain: true, push: true, pull: true },
  } });
  comprobar("ser admin de OTRO repo no autoriza (el repo esta fijo en el server)",
    (await accesoAlRepoValido("token-admin-ajeno", gh)) === false);
}

// --- sin token / token vacio ---
for (const vacio of [undefined, null, "", "   "]) {
  const gh = githubFalso({});
  comprobar(`sin token (${JSON.stringify(vacio)}) no autoriza`,
    (await accesoAlRepoValido(vacio, gh)) === false);
}

// --- token invalido: GitHub responde 404/401 ---
{
  const gh = githubFalso({});
  comprobar("un token invalido no autoriza",
    (await accesoAlRepoValido("token-trucho", gh)) === false);
}

// --- GitHub caido: falla CERRADO, no abierto ---
{
  const gh = githubFalso({ "token-del-workflow": { lanzar: true } });
  comprobar("si GitHub no responde, NO autoriza (falla cerrado)",
    (await accesoAlRepoValido("token-del-workflow", gh)) === false);
}

// --- el repo esta fijo en el codigo, no viene del request ---
{
  const { readFileSync } = await import("node:fs");
  const src = readFileSync(new URL("../api/_owner_github.js", import.meta.url), "utf8");
  comprobar("el repo esta escrito fijo en el servidor (no se toma del request)",
    /const REPO_ESPERADO = "vieraschiavi\/Amazon-Fba"/.test(src));
  comprobar("la URL consultada usa esa constante, no un parametro",
    /api\.github\.com\/repos\/\$\{REPO_ESPERADO\}/.test(src));
}

console.log("");
if (fallas) {
  console.error(`FALLO: ${fallas} problema(s) en la autorizacion del build owner.`);
  process.exit(1);
}
console.log("OK: la licencia de dueño solo se autoriza con acceso real al repo "
  + "privado, y falla cerrada ante cualquier duda.");
