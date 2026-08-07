// api/_owner_github.js — Autoriza el build OWNER probando acceso al repo privado.
//
// POR QUE ASI
// -----------
// La licencia de dueño la pide el workflow de GitHub para hornearla dentro del
// instalador interno. La pregunta es como distingue el servidor "esto lo pide mi
// build" de "esto lo pide cualquiera desde la web".
//
// Pedirle al dueño que configure un token a mano en dos lados era friccion sin
// seguridad real: quien puede correr el workflow YA tiene acceso total al repo
// privado. Asi que la autorizacion ES el acceso al repo.
//
// El workflow manda el GITHUB_TOKEN que Actions le da solo (efimero, con alcance
// a este repo). Aca se verifica contra la API de GitHub: si ese token puede leer
// el repo PRIVADO, quien llama es el dueño o alguien a quien el dueño le dio
// acceso. Nadie desde la web tiene un token asi.
//
// Resultado: cero configuracion, y el camino publico sigue cerrado.
//
// El prefijo "_" hace que Vercel NO trate este archivo como una ruta.

// Repo FIJO, escrito aca y nunca tomado del request: si viniera del cliente,
// cualquiera apuntaria a un repo suyo, sacaria un 200 y se colaria.
const REPO_ESPERADO = "vieraschiavi/Amazon-Fba";

/**
 * ¿El token prueba acceso de lectura al repo privado del producto?
 * Devuelve false ante cualquier duda (falla cerrado). Nunca lanza.
 */
export async function accesoAlRepoValido(token, fetchImpl = fetch) {
  const limpio = String(token || "").trim();
  if (!limpio) return false;
  try {
    const r = await fetchImpl(`https://api.github.com/repos/${REPO_ESPERADO}`, {
      headers: {
        authorization: `Bearer ${limpio}`,
        accept: "application/vnd.github+json",
        "user-agent": "mvfba-owner-build",
      },
    });
    if (!r.ok) return false;
    const d = await r.json();
    // Dos comprobaciones, no una:
    //   full_name  -> que sea EXACTAMENTE este repo y no otro homonimo;
    //   private    -> si algun dia el repo se hiciera publico, un token
    //                 cualquiera podria leerlo y esto dejaria de probar nada.
    //                 Mejor que deje de autorizar a que autorice de mas.
    return d && d.full_name === REPO_ESPERADO && d.private === true;
  } catch (_) {
    return false;   // sin red, token invalido, respuesta rara: no autoriza
  }
}

export const REPO_OWNER_ESPERADO = REPO_ESPERADO;
