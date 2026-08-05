/* verificar_owner_github.mjs — La licencia de dueño se autoriza probando
 * acceso al repo PRIVADO, y no de otra forma.
 *
 * POR QUE EXISTE: el camino ?dueno=1 emite una licencia Pro gratis. Si se
 * autorizara mal, cualquiera deja de pagar el producto. Las trampas concretas
 * que este test fija:
 *
 *   - un token que da 200 sobre OTRO repo no sirve (si el repo se tomara del
 *     request, cualquiera apuntaria a uno suyo y entraria);
 *   - un repo PUBLICO no sirve como prueba (lo lee cualquiera);
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

// --- el repo dejo de ser privado: ya no prueba nada ---
{
  const gh = githubFalso({ "token-cualquiera": { full_name: REPO, private: false } });
  comprobar("si el repo fuera PUBLICO no autoriza (leerlo dejaria de probar acceso)",
    (await accesoAlRepoValido("token-cualquiera", gh)) === false);
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
